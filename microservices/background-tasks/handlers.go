package main

import (
	"context"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

// BackgroundTaskHandlers handles HTTP requests for background tasks
type BackgroundTaskHandlers struct {
	queue           *TaskQueue
	workerPool      *WorkerPool
	notificationSvc *NotificationService
	logger          *zap.Logger
}

// NewBackgroundTaskHandlers creates new HTTP handlers
func NewBackgroundTaskHandlers(
	queue *TaskQueue, 
	workerPool *WorkerPool,
	notificationSvc *NotificationService, 
	logger *zap.Logger,
) *BackgroundTaskHandlers {
	return &BackgroundTaskHandlers{
		queue:           queue,
		workerPool:      workerPool,
		notificationSvc: notificationSvc,
		logger:          logger,
	}
}

// SubmitTask submits a new background task
func (h *BackgroundTaskHandlers) SubmitTask(c *gin.Context) {
	var req TaskSubmissionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body: " + err.Error(),
		})
		return
	}

	// Validate task type
	if req.Type != "data_analysis" && req.Type != "research" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid task type. Supported types: data_analysis, research",
		})
		return
	}

	// Set default priority if not provided
	if req.Priority == 0 {
		req.Priority = 2 // Normal priority
	}

	// Validate priority
	if req.Priority < 1 || req.Priority > 3 {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid priority. Must be 1 (high), 2 (normal), or 3 (low)",
		})
		return
	}

	// Validate required data based on task type
	if req.Type == "data_analysis" {
		if _, exists := req.Data["data_description"]; !exists {
			c.JSON(http.StatusBadRequest, APIResponse{
				Success: false,
				Error:   "Missing required field: data_description",
			})
			return
		}
	} else if req.Type == "research" {
		if _, exists := req.Data["research_topic"]; !exists {
			c.JSON(http.StatusBadRequest, APIResponse{
				Success: false,
				Error:   "Missing required field: research_topic",
			})
			return
		}
	}

	// Create task
	task := NewTask(req.Type, req.UserID, req.SessionID, req.Data)
	task.Priority = req.Priority

	// Enqueue task
	err := h.queue.Enqueue(task)
	if err != nil {
		h.logger.Error("Failed to enqueue task", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to submit task",
		})
		return
	}

	h.logger.Info("Task submitted", 
		zap.String("task_id", task.ID),
		zap.String("type", task.Type),
		zap.String("user_id", req.UserID))

	c.JSON(http.StatusAccepted, APIResponse{
		Success: true,
		Message: "Task submitted successfully",
		Data: map[string]interface{}{
			"task_id":   task.ID,
			"status":    task.Status,
			"priority":  task.Priority,
			"submitted_at": task.CreatedAt,
		},
	})
}

// GetTaskStatus returns the status of a specific task
func (h *BackgroundTaskHandlers) GetTaskStatus(c *gin.Context) {
	taskID := c.Param("task_id")
	if taskID == "" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Task ID is required",
		})
		return
	}

	task, err := h.queue.GetTaskStatus(taskID)
	if err != nil {
		h.logger.Error("Failed to get task status", zap.String("task_id", taskID), zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get task status",
		})
		return
	}

	if task == nil {
		c.JSON(http.StatusNotFound, APIResponse{
			Success: false,
			Error:   "Task not found",
		})
		return
	}

	// Calculate estimated time remaining
	estimatedTime := 0
	if task.Status == "running" {
		switch task.Type {
		case "data_analysis":
			estimatedTime = 2
		case "research":
			estimatedTime = 1
		}
	}

	response := TaskStatusResponse{
		TaskID:          task.ID,
		Status:          task.Status,
		Progress:        task.GetProgress(),
		EstimatedTime:   estimatedTime,
		DurationSeconds: task.DurationSeconds,
		Result:          task.Result,
		Error:           task.Error,
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    response,
	})
}

// GetUserTasks returns tasks for a specific user
func (h *BackgroundTaskHandlers) GetUserTasks(c *gin.Context) {
	userID := c.Param("user_id")
	if userID == "" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "User ID is required",
		})
		return
	}

	limitStr := c.DefaultQuery("limit", "20")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}

	tasks, err := h.queue.GetTasksByUser(userID, limit)
	if err != nil {
		h.logger.Error("Failed to get user tasks", zap.String("user_id", userID), zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get user tasks",
		})
		return
	}

	// Convert to API response format
	apiTasks := make([]Task, len(tasks))
	for i, task := range tasks {
		apiTasks[i] = *task
	}

	response := TaskListResponse{
		Tasks: apiTasks,
		Total: len(apiTasks),
		Limit: limit,
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    response,
	})
}

// GetServiceStats returns service statistics
func (h *BackgroundTaskHandlers) GetServiceStats(c *gin.Context) {
	stats := h.workerPool.GetStats()

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    stats,
	})
}

// GetWorkerStats returns worker statistics
func (h *BackgroundTaskHandlers) GetWorkerStats(c *gin.Context) {
	workerID := c.Param("worker_id")
	if workerID == "" {
		// Return all workers
		stats := h.workerPool.GetStats()
		c.JSON(http.StatusOK, APIResponse{
			Success: true,
			Data:    stats.Workers,
		})
		return
	}

	worker := h.workerPool.GetWorkerByID(workerID)
	if worker == nil {
		c.JSON(http.StatusNotFound, APIResponse{
			Success: false,
			Error:   "Worker not found",
		})
		return
	}

	stats := worker.GetStats()
	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    stats,
	})
}

// GetNotifications returns notifications for a user
func (h *BackgroundTaskHandlers) GetNotifications(c *gin.Context) {
	userID := c.Param("user_id")
	if userID == "" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "User ID is required",
		})
		return
	}

	limitStr := c.DefaultQuery("limit", "20")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 20
	}
	if limit > 50 {
		limit = 50
	}

	notifications, err := h.notificationSvc.GetNotifications(userID, limit)
	if err != nil {
		h.logger.Error("Failed to get notifications", zap.String("user_id", userID), zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get notifications",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data: map[string]interface{}{
			"notifications": notifications,
			"total":         len(notifications),
		},
	})
}

// ClearNotifications clears notifications for a user
func (h *BackgroundTaskHandlers) ClearNotifications(c *gin.Context) {
	userID := c.Param("user_id")
	if userID == "" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "User ID is required",
		})
		return
	}

	err := h.notificationSvc.ClearNotifications(userID)
	if err != nil {
		h.logger.Error("Failed to clear notifications", zap.String("user_id", userID), zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to clear notifications",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Notifications cleared successfully",
	})
}

// SubmitDataAnalysisTask submits a data analysis task (convenience endpoint)
func (h *BackgroundTaskHandlers) SubmitDataAnalysisTask(c *gin.Context) {
	var req struct {
		UserID          string `json:"user_id" binding:"required"`
		SessionID       string `json:"session_id" binding:"required"`
		DataDescription string `json:"data_description" binding:"required"`
		Priority        int    `json:"priority"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body: " + err.Error(),
		})
		return
	}

	// Convert to task submission request
	taskReq := TaskSubmissionRequest{
		Type:      "data_analysis",
		UserID:    req.UserID,
		SessionID: req.SessionID,
		Data: map[string]interface{}{
			"data_description": req.DataDescription,
		},
		Priority: req.Priority,
	}

	// Use the same logic as SubmitTask
	c.Set("taskRequest", taskReq)
	h.SubmitTask(c)
}

// SubmitResearchTask submits a research task (convenience endpoint)
func (h *BackgroundTaskHandlers) SubmitResearchTask(c *gin.Context) {
	var req struct {
		UserID        string `json:"user_id" binding:"required"`
		SessionID     string `json:"session_id" binding:"required"`
		ResearchTopic string `json:"research_topic" binding:"required"`
		Priority      int    `json:"priority"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body: " + err.Error(),
		})
		return
	}

	// Convert to task submission request
	taskReq := TaskSubmissionRequest{
		Type:      "research",
		UserID:    req.UserID,
		SessionID: req.SessionID,
		Data: map[string]interface{}{
			"research_topic": req.ResearchTopic,
		},
		Priority: req.Priority,
	}

	// Use the same logic as SubmitTask
	c.Set("taskRequest", taskReq)
	h.SubmitTask(c)
}

// HealthCheck endpoint
func (h *BackgroundTaskHandlers) HealthCheck(c *gin.Context) {
	// Check queue health
	queueLength, err := h.queue.GetQueueLength()
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, HealthCheckResponse{
			Status:    "unhealthy",
			Timestamp: c.Request.Context().Value("request_time").(time.Time),
			Service:   "background-tasks-service-go",
			Version:   "1.0.0",
			Details: map[string]interface{}{
				"error": "Queue health check failed: " + err.Error(),
			},
		})
		return
	}

	// Get service stats
	stats := h.workerPool.GetStats()

	// Determine health status
	status := "healthy"
	if stats.ActiveWorkers == 0 {
		status = "degraded"
	}

	c.JSON(http.StatusOK, HealthCheckResponse{
		Status:    status,
		Timestamp: c.Request.Context().Value("request_time").(time.Time),
		Service:   "background-tasks-service-go",
		Version:   "1.0.0",
		Details: map[string]interface{}{
			"queue_length":    queueLength,
			"active_workers":  stats.ActiveWorkers,
			"total_tasks":     stats.TotalTasks,
			"success_rate":    stats.SuccessRate,
			"tasks_per_minute": stats.TasksPerMinute,
		},
	})
}

// GetAnalytics returns analytics data
func (h *BackgroundTaskHandlers) GetAnalytics(c *gin.Context) {
	counters, err := h.notificationSvc.analytics.GetCounters()
	if err != nil {
		h.logger.Error("Failed to get analytics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get analytics",
		})
		return
	}

	// Get queue stats
	queueStats, err := h.queue.GetQueueStats()
	if err != nil {
		h.logger.Error("Failed to get queue stats", zap.Error(err))
		queueStats = make(map[string]interface{})
	}

	// Combine analytics
	analytics := map[string]interface{}{
		"counters":   counters,
		"queue_stats": queueStats,
		"service_stats": h.workerPool.GetStats(),
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    analytics,
	})
}

// PurgeTasks removes old completed tasks
func (h *BackgroundTaskHandlers) PurgeTasks(c *gin.Context) {
	hoursStr := c.DefaultQuery("older_than_hours", "48")
	hours, err := strconv.Atoi(hoursStr)
	if err != nil || hours <= 0 {
		hours = 48
	}

	deleted, err := h.queue.PurgeCompletedTasks(time.Duration(hours) * time.Hour)
	if err != nil {
		h.logger.Error("Failed to purge tasks", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to purge tasks",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: fmt.Sprintf("Purged %d completed tasks", deleted),
		Data: map[string]interface{}{
			"deleted_count": deleted,
		},
	})
}

// Middleware for request timing
func RequestTimingMiddleware() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), "request_time", time.Now()))
		c.Next()
	})
}