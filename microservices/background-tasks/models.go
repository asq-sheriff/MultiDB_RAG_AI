package main

import (
	"time"

	"github.com/google/uuid"
)

// TaskResult represents the result of a background task
type TaskResult struct {
	TaskID           string      `json:"task_id"`
	Success          bool        `json:"success"`
	Result           interface{} `json:"result,omitempty"`
	Error            string      `json:"error,omitempty"`
	DurationSeconds  float64     `json:"duration_seconds"`
	CompletedAt      time.Time   `json:"completed_at"`
}

// Task represents a background task
type Task struct {
	ID              string                 `json:"id"`
	Type            string                 `json:"type"`
	Status          string                 `json:"status"` // pending, running, completed, failed
	UserID          string                 `json:"user_id"`
	SessionID       string                 `json:"session_id"`
	Data            map[string]interface{} `json:"data"`
	Priority        int                    `json:"priority"` // 1=high, 2=normal, 3=low
	CreatedAt       time.Time              `json:"created_at"`
	StartedAt       *time.Time             `json:"started_at,omitempty"`
	CompletedAt     *time.Time             `json:"completed_at,omitempty"`
	DurationSeconds float64                `json:"duration_seconds"`
	Result          interface{}            `json:"result,omitempty"`
	Error           string                 `json:"error,omitempty"`
	RetryCount      int                    `json:"retry_count"`
	MaxRetries      int                    `json:"max_retries"`
}

// TaskSubmissionRequest represents a request to submit a task
type TaskSubmissionRequest struct {
	Type      string                 `json:"type" binding:"required"`
	UserID    string                 `json:"user_id" binding:"required"`
	SessionID string                 `json:"session_id" binding:"required"`
	Data      map[string]interface{} `json:"data"`
	Priority  int                    `json:"priority"`
}

// TaskStatusResponse represents the status of a task
type TaskStatusResponse struct {
	TaskID          string      `json:"task_id"`
	Status          string      `json:"status"`
	Progress        float64     `json:"progress,omitempty"`
	EstimatedTime   int         `json:"estimated_time_seconds,omitempty"`
	DurationSeconds float64     `json:"duration_seconds,omitempty"`
	Result          interface{} `json:"result,omitempty"`
	Error           string      `json:"error,omitempty"`
}

// DataAnalysisResult represents the result of a data analysis task
type DataAnalysisResult struct {
	Summary          string   `json:"summary"`
	Insights         []string `json:"insights"`
	ChartsGenerated  int      `json:"charts_generated"`
	Recommendations  string   `json:"recommendations"`
	ConfidenceLevel  string   `json:"confidence_level"`
	ProcessingSteps  []string `json:"processing_steps"`
}

// ResearchResult represents the result of a research task
type ResearchResult struct {
	Topic           string    `json:"topic"`
	Summary         string    `json:"summary"`
	SourcesFound    int       `json:"sources_found"`
	KeyFindings     []string  `json:"key_findings"`
	ResearchDate    time.Time `json:"research_date"`
	ConfidenceLevel string    `json:"confidence_level"`
	References      []string  `json:"references,omitempty"`
}

// Notification represents a notification to be sent to users
type Notification struct {
	Type    string                 `json:"type"` // success, error, info, warning
	Title   string                 `json:"title"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data"`
}

// WorkerStats represents statistics about a worker
type WorkerStats struct {
	ID              string    `json:"id"`
	Status          string    `json:"status"` // idle, busy, stopped
	TasksProcessed  int       `json:"tasks_processed"`
	TasksSucceeded  int       `json:"tasks_succeeded"`
	TasksFailed     int       `json:"tasks_failed"`
	LastTaskID      string    `json:"last_task_id,omitempty"`
	LastTaskTime    time.Time `json:"last_task_time,omitempty"`
	AverageTaskTime float64   `json:"average_task_time_seconds"`
	StartedAt       time.Time `json:"started_at"`
}

// ServiceStats represents overall service statistics
type ServiceStats struct {
	TotalTasks       int64         `json:"total_tasks"`
	PendingTasks     int64         `json:"pending_tasks"`
	RunningTasks     int64         `json:"running_tasks"`
	CompletedTasks   int64         `json:"completed_tasks"`
	FailedTasks      int64         `json:"failed_tasks"`
	ActiveWorkers    int           `json:"active_workers"`
	Workers          []WorkerStats `json:"workers"`
	Uptime           time.Duration `json:"uptime"`
	TasksPerMinute   float64       `json:"tasks_per_minute"`
	SuccessRate      float64       `json:"success_rate_percent"`
}

// APIResponse represents a generic API response
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// TaskListResponse represents a list of tasks response
type TaskListResponse struct {
	Tasks []Task `json:"tasks"`
	Total int    `json:"total"`
	Page  int    `json:"page"`
	Limit int    `json:"limit"`
}

// HealthCheckResponse represents health check response
type HealthCheckResponse struct {
	Status    string                 `json:"status"`
	Timestamp time.Time              `json:"timestamp"`
	Service   string                 `json:"service"`
	Version   string                 `json:"version"`
	Details   map[string]interface{} `json:"details,omitempty"`
}

// NewTask creates a new task with default values
func NewTask(taskType, userID, sessionID string, data map[string]interface{}) *Task {
	now := time.Now()
	task := &Task{
		ID:         uuid.New().String(),
		Type:       taskType,
		Status:     "pending",
		UserID:     userID,
		SessionID:  sessionID,
		Data:       data,
		Priority:   2, // Normal priority by default
		CreatedAt:  now,
		MaxRetries: 3,
	}

	if data == nil {
		task.Data = make(map[string]interface{})
	}

	return task
}

// IsCompleted returns true if the task is completed (success or failure)
func (t *Task) IsCompleted() bool {
	return t.Status == "completed" || t.Status == "failed"
}

// IsRunning returns true if the task is currently running
func (t *Task) IsRunning() bool {
	return t.Status == "running"
}

// CanRetry returns true if the task can be retried
func (t *Task) CanRetry() bool {
	return t.Status == "failed" && t.RetryCount < t.MaxRetries
}

// MarkStarted marks the task as started
func (t *Task) MarkStarted() {
	now := time.Now()
	t.Status = "running"
	t.StartedAt = &now
}

// MarkCompleted marks the task as successfully completed
func (t *Task) MarkCompleted(result interface{}) {
	now := time.Now()
	t.Status = "completed"
	t.CompletedAt = &now
	t.Result = result
	if t.StartedAt != nil {
		t.DurationSeconds = now.Sub(*t.StartedAt).Seconds()
	}
}

// MarkFailed marks the task as failed
func (t *Task) MarkFailed(err error) {
	now := time.Now()
	t.Status = "failed"
	t.CompletedAt = &now
	t.Error = err.Error()
	t.RetryCount++
	if t.StartedAt != nil {
		t.DurationSeconds = now.Sub(*t.StartedAt).Seconds()
	}
}

// GetProgress calculates task progress based on status
func (t *Task) GetProgress() float64 {
	switch t.Status {
	case "pending":
		return 0.0
	case "running":
		// Estimate progress based on time elapsed and task type
		if t.StartedAt == nil {
			return 0.1
		}
		elapsed := time.Since(*t.StartedAt).Seconds()
		switch t.Type {
		case "data_analysis":
			// Simulate progress for data analysis (estimate 2-5 seconds)
			return min(90.0, elapsed/3.0*100.0)
		case "research":
			// Simulate progress for research (estimate 1-2 seconds)
			return min(90.0, elapsed/1.5*100.0)
		default:
			return min(90.0, elapsed/2.0*100.0)
		}
	case "completed":
		return 100.0
	case "failed":
		return 0.0
	default:
		return 0.0
	}
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}