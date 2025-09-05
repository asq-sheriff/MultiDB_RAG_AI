package main

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

// Worker represents a background task worker
type Worker struct {
	ID              string
	queue           *TaskQueue
	notificationSvc *NotificationService
	logger          *zap.Logger
	ctx             context.Context
	cancel          context.CancelFunc
	stats           WorkerStats
	mu              sync.RWMutex
	processingTask  *Task
}

// WorkerPool manages a pool of workers
type WorkerPool struct {
	workers         []*Worker
	queue           *TaskQueue
	notificationSvc *NotificationService
	logger          *zap.Logger
	ctx             context.Context
	cancel          context.CancelFunc
	workerCount     int
	wg              sync.WaitGroup
	mu              sync.RWMutex
	startTime       time.Time
}

// NewWorker creates a new worker
func NewWorker(id string, queue *TaskQueue, notificationSvc *NotificationService, logger *zap.Logger) *Worker {
	ctx, cancel := context.WithCancel(context.Background())
	
	return &Worker{
		ID:              id,
		queue:           queue,
		notificationSvc: notificationSvc,
		logger:          logger.With(zap.String("worker_id", id)),
		ctx:             ctx,
		cancel:          cancel,
		stats: WorkerStats{
			ID:        id,
			Status:    "idle",
			StartedAt: time.Now(),
		},
	}
}

// Start starts the worker
func (w *Worker) Start() {
	w.logger.Info("Starting worker")
	
	go w.run()
}

// Stop stops the worker
func (w *Worker) Stop() {
	w.logger.Info("Stopping worker")
	w.cancel()
}

// GetStats returns worker statistics
func (w *Worker) GetStats() WorkerStats {
	w.mu.RLock()
	defer w.mu.RUnlock()
	
	stats := w.stats
	if w.processingTask != nil {
		stats.LastTaskID = w.processingTask.ID
		stats.LastTaskTime = *w.processingTask.StartedAt
	}
	
	// Calculate average task time
	if stats.TasksProcessed > 0 {
		totalTime := time.Since(stats.StartedAt).Seconds()
		stats.AverageTaskTime = totalTime / float64(stats.TasksProcessed)
	}
	
	return stats
}

// run is the main worker loop
func (w *Worker) run() {
	defer func() {
		if r := recover(); r != nil {
			w.logger.Error("Worker panic recovered", zap.Any("panic", r))
		}
	}()

	for {
		select {
		case <-w.ctx.Done():
			w.logger.Info("Worker stopping")
			return
		default:
			// Try to get a task from the queue
			task, err := w.queue.Dequeue(5 * time.Second)
			if err != nil {
				w.logger.Error("Failed to dequeue task", zap.Error(err))
				time.Sleep(time.Second)
				continue
			}
			
			if task == nil {
				// No tasks available, continue polling
				continue
			}
			
			// Process the task
			w.processTask(task)
		}
	}
}

// processTask processes a single task
func (w *Worker) processTask(task *Task) {
	w.mu.Lock()
	w.processingTask = task
	w.stats.Status = "busy"
	w.mu.Unlock()
	
	defer func() {
		w.mu.Lock()
		w.processingTask = nil
		w.stats.Status = "idle"
		w.stats.TasksProcessed++
		w.mu.Unlock()
	}()

	w.logger.Info("Processing task",
		zap.String("task_id", task.ID),
		zap.String("type", task.Type),
		zap.String("user_id", task.UserID))

	// Mark task as started
	task.MarkStarted()
	err := w.queue.UpdateTaskStatus(task)
	if err != nil {
		w.logger.Error("Failed to update task status", zap.Error(err))
	}

	// Process based on task type
	var result interface{}
	var taskErr error

	switch task.Type {
	case "data_analysis":
		result, taskErr = w.processDataAnalysis(task)
	case "research":
		result, taskErr = w.processResearch(task)
	default:
		taskErr = fmt.Errorf("unknown task type: %s", task.Type)
	}

	// Update task with result
	if taskErr != nil {
		task.MarkFailed(taskErr)
		w.stats.TasksFailed++
		w.logger.Error("Task failed", 
			zap.String("task_id", task.ID), 
			zap.Error(taskErr))
		
		// Send error notification
		w.notificationSvc.SendErrorNotification(task, taskErr.Error())
		
		// Check if task can be retried
		if task.CanRetry() {
			w.logger.Info("Retrying task", 
				zap.String("task_id", task.ID),
				zap.Int("retry", task.RetryCount))
			task.Status = "pending" // Reset to pending for retry
			err = w.queue.Enqueue(task)
			if err != nil {
				w.logger.Error("Failed to retry task", zap.Error(err))
			}
		}
	} else {
		task.MarkCompleted(result)
		w.stats.TasksSucceeded++
		w.logger.Info("Task completed successfully", 
			zap.String("task_id", task.ID),
			zap.Float64("duration", task.DurationSeconds))
		
		// Send completion notification
		w.notificationSvc.SendCompletionNotification(task, result)
	}

	// Update task status
	err = w.queue.UpdateTaskStatus(task)
	if err != nil {
		w.logger.Error("Failed to update task status", zap.Error(err))
	}
}

// processDataAnalysis processes a data analysis task
func (w *Worker) processDataAnalysis(task *Task) (interface{}, error) {
	dataDescription, ok := task.Data["data_description"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid data_description")
	}

	// Simulate processing steps with realistic timing
	steps := []string{"Loading data", "Preprocessing", "Analysis", "Generating report"}
	var processingTime time.Duration

	// Determine processing time based on data description
	if contains(dataDescription, "large") {
		processingTime = 2 * time.Second
	} else if contains(dataDescription, "complex") {
		processingTime = 1 * time.Second
	} else {
		processingTime = 1 * time.Second
	}

	stepDuration := processingTime / time.Duration(len(steps))
	processedSteps := make([]string, 0, len(steps))

	for i, step := range steps {
		select {
		case <-w.ctx.Done():
			return nil, fmt.Errorf("task cancelled")
		default:
			time.Sleep(stepDuration)
			processedSteps = append(processedSteps, step)
			w.logger.Debug("Processing step", 
				zap.String("task_id", task.ID),
				zap.String("step", step),
				zap.Int("progress", (i+1)*100/len(steps)))
		}
	}

	// Generate mock analysis result
	result := DataAnalysisResult{
		Summary:         fmt.Sprintf("Analysis of '%s' completed successfully", dataDescription),
		Insights: []string{
			"Data shows clear trends and patterns",
			"Identified 3 key areas for improvement",
			"Correlation strength: 0.85",
			"Recommended next steps: Further investigation needed",
		},
		ChartsGenerated:  2,
		Recommendations:  "Consider expanding dataset for deeper insights",
		ConfidenceLevel:  "High",
		ProcessingSteps:  processedSteps,
	}

	return result, nil
}

// processResearch processes a research task
func (w *Worker) processResearch(task *Task) (interface{}, error) {
	researchTopic, ok := task.Data["research_topic"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid research_topic")
	}

	// Simulate research steps
	steps := []string{
		"Searching academic databases",
		"Analyzing sources", 
		"Cross-referencing information",
		"Compiling findings",
	}

	stepDuration := 250 * time.Millisecond

	for i, step := range steps {
		select {
		case <-w.ctx.Done():
			return nil, fmt.Errorf("task cancelled")
		default:
			time.Sleep(stepDuration)
			w.logger.Debug("Research step", 
				zap.String("task_id", task.ID),
				zap.String("step", step),
				zap.Int("progress", (i+1)*100/len(steps)))
		}
	}

	// Generate mock research result
	result := ResearchResult{
		Topic:           researchTopic,
		Summary:         fmt.Sprintf("Comprehensive research on '%s' completed", researchTopic),
		SourcesFound:    15,
		KeyFindings: []string{
			fmt.Sprintf("Latest developments in %s", researchTopic),
			"Industry trends and future outlook",
			"Best practices and recommendations",
		},
		ResearchDate:    time.Now(),
		ConfidenceLevel: "High",
		References: []string{
			"Academic Source 1",
			"Industry Report 2023",
			"Expert Analysis",
		},
	}

	return result, nil
}

// NewWorkerPool creates a new worker pool
func NewWorkerPool(workerCount int, queue *TaskQueue, notificationSvc *NotificationService, logger *zap.Logger) *WorkerPool {
	ctx, cancel := context.WithCancel(context.Background())
	
	pool := &WorkerPool{
		workers:         make([]*Worker, 0, workerCount),
		queue:           queue,
		notificationSvc: notificationSvc,
		logger:          logger,
		ctx:             ctx,
		cancel:          cancel,
		workerCount:     workerCount,
		startTime:       time.Now(),
	}
	
	// Create workers
	for i := 0; i < workerCount; i++ {
		workerID := fmt.Sprintf("worker-%s", uuid.New().String()[:8])
		worker := NewWorker(workerID, queue, notificationSvc, logger)
		pool.workers = append(pool.workers, worker)
	}
	
	return pool
}

// Start starts all workers in the pool
func (p *WorkerPool) Start() {
	p.logger.Info("Starting worker pool", zap.Int("worker_count", p.workerCount))
	
	p.mu.Lock()
	defer p.mu.Unlock()
	
	for _, worker := range p.workers {
		p.wg.Add(1)
		go func(w *Worker) {
			defer p.wg.Done()
			w.Start()
			
			// Keep worker alive until context is cancelled
			<-p.ctx.Done()
			w.Stop()
		}(worker)
	}
}

// Stop stops all workers in the pool
func (p *WorkerPool) Stop() {
	p.logger.Info("Stopping worker pool")
	
	p.cancel()
	p.wg.Wait()
	
	p.logger.Info("Worker pool stopped")
}

// GetStats returns statistics for all workers
func (p *WorkerPool) GetStats() ServiceStats {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	workerStats := make([]WorkerStats, 0, len(p.workers))
	var totalTasks, succeededTasks, failedTasks int64
	
	activeWorkers := 0
	for _, worker := range p.workers {
		stats := worker.GetStats()
		workerStats = append(workerStats, stats)
		
		totalTasks += int64(stats.TasksProcessed)
		succeededTasks += int64(stats.TasksSucceeded)
		failedTasks += int64(stats.TasksFailed)
		
		if stats.Status == "busy" {
			activeWorkers++
		}
	}
	
	// Get queue stats
	queueStats, err := p.queue.GetQueueStats()
	pendingTasks := int64(0)
	runningTasks := int64(activeWorkers)
	completedTasks := succeededTasks
	
	if err == nil {
		if pending, ok := queueStats["total_pending"].(int64); ok {
			pendingTasks = pending
		}
		
		if statusCounts, ok := queueStats["status_counts"].(map[string]int); ok {
			if completed, exists := statusCounts["completed"]; exists {
				completedTasks = int64(completed)
			}
		}
	}
	
	// Calculate success rate
	successRate := float64(0)
	if totalTasks > 0 {
		successRate = float64(succeededTasks) / float64(totalTasks) * 100
	}
	
	// Calculate tasks per minute
	uptime := time.Since(p.startTime)
	tasksPerMinute := float64(0)
	if uptime.Minutes() > 0 {
		tasksPerMinute = float64(totalTasks) / uptime.Minutes()
	}
	
	return ServiceStats{
		TotalTasks:     totalTasks,
		PendingTasks:   pendingTasks,
		RunningTasks:   runningTasks,
		CompletedTasks: completedTasks,
		FailedTasks:    failedTasks,
		ActiveWorkers:  activeWorkers,
		Workers:        workerStats,
		Uptime:         uptime,
		TasksPerMinute: tasksPerMinute,
		SuccessRate:    successRate,
	}
}

// GetWorkerByID returns a worker by ID
func (p *WorkerPool) GetWorkerByID(workerID string) *Worker {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	for _, worker := range p.workers {
		if worker.ID == workerID {
			return worker
		}
	}
	
	return nil
}

// Helper function
func contains(s, substr string) bool {
	return len(s) >= len(substr) && 
		   (s == substr || 
		    s[:len(substr)] == substr || 
		    s[len(s)-len(substr):] == substr ||
		    containsSubstring(s, substr))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}