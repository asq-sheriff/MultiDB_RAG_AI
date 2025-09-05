package main

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// TaskQueue manages task queuing and distribution using Redis
type TaskQueue struct {
	client    *redis.Client
	logger    *zap.Logger
	ctx       context.Context
	queueKey  string
	statusKey string
	mu        sync.RWMutex
}

// NewTaskQueue creates a new task queue
func NewTaskQueue(redisURL string, logger *zap.Logger) (*TaskQueue, error) {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	client := redis.NewClient(opt)
	ctx := context.Background()

	// Test connection
	_, err = client.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &TaskQueue{
		client:    client,
		logger:    logger,
		ctx:       ctx,
		queueKey:  "background_tasks:queue",
		statusKey: "background_tasks:status:",
	}, nil
}

// Close closes the Redis connection
func (q *TaskQueue) Close() error {
	return q.client.Close()
}

// Enqueue adds a task to the queue
func (q *TaskQueue) Enqueue(task *Task) error {
	q.mu.Lock()
	defer q.mu.Unlock()

	// Serialize task
	taskData, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("failed to marshal task: %w", err)
	}

	// Store task status
	statusKey := q.statusKey + task.ID
	err = q.client.Set(q.ctx, statusKey, taskData, 24*time.Hour).Err()
	if err != nil {
		return fmt.Errorf("failed to store task status: %w", err)
	}

	// Add to priority queue based on priority
	var queueKey string
	switch task.Priority {
	case 1:
		queueKey = q.queueKey + ":high"
	case 3:
		queueKey = q.queueKey + ":low"
	default:
		queueKey = q.queueKey + ":normal"
	}

	// Add task ID to appropriate priority queue
	err = q.client.LPush(q.ctx, queueKey, task.ID).Err()
	if err != nil {
		// Clean up status if queue push failed
		q.client.Del(q.ctx, statusKey)
		return fmt.Errorf("failed to enqueue task: %w", err)
	}

	q.logger.Info("Task enqueued",
		zap.String("task_id", task.ID),
		zap.String("type", task.Type),
		zap.Int("priority", task.Priority),
		zap.String("user_id", task.UserID))

	return nil
}

// Dequeue gets the next task from the queue (priority order: high, normal, low)
func (q *TaskQueue) Dequeue(timeout time.Duration) (*Task, error) {
	q.mu.Lock()
	defer q.mu.Unlock()

	// Try priority queues in order
	queues := []string{
		q.queueKey + ":high",
		q.queueKey + ":normal",
		q.queueKey + ":low",
	}

	// Use BRPOP to block until a task is available
	result, err := q.client.BRPop(q.ctx, timeout, queues...).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Timeout - no tasks available
		}
		return nil, fmt.Errorf("failed to dequeue task: %w", err)
	}

	taskID := result[1]
	statusKey := q.statusKey + taskID

	// Get task data
	taskData, err := q.client.Get(q.ctx, statusKey).Result()
	if err != nil {
		q.logger.Error("Failed to get task data", zap.String("task_id", taskID), zap.Error(err))
		return nil, fmt.Errorf("failed to get task data: %w", err)
	}

	// Deserialize task
	var task Task
	err = json.Unmarshal([]byte(taskData), &task)
	if err != nil {
		q.logger.Error("Failed to unmarshal task", zap.String("task_id", taskID), zap.Error(err))
		return nil, fmt.Errorf("failed to unmarshal task: %w", err)
	}

	return &task, nil
}

// UpdateTaskStatus updates the status of a task
func (q *TaskQueue) UpdateTaskStatus(task *Task) error {
	q.mu.Lock()
	defer q.mu.Unlock()

	statusKey := q.statusKey + task.ID

	// Serialize updated task
	taskData, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("failed to marshal task: %w", err)
	}

	// Update status with extended TTL for completed tasks
	var ttl time.Duration
	if task.IsCompleted() {
		ttl = 48 * time.Hour // Keep completed tasks longer for history
	} else {
		ttl = 24 * time.Hour
	}

	err = q.client.Set(q.ctx, statusKey, taskData, ttl).Err()
	if err != nil {
		return fmt.Errorf("failed to update task status: %w", err)
	}

	return nil
}

// GetTaskStatus retrieves the status of a task
func (q *TaskQueue) GetTaskStatus(taskID string) (*Task, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()

	statusKey := q.statusKey + taskID

	taskData, err := q.client.Get(q.ctx, statusKey).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Task not found
		}
		return nil, fmt.Errorf("failed to get task status: %w", err)
	}

	var task Task
	err = json.Unmarshal([]byte(taskData), &task)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal task: %w", err)
	}

	return &task, nil
}

// GetQueueLength returns the total number of pending tasks across all priority queues
func (q *TaskQueue) GetQueueLength() (int64, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()

	queues := []string{
		q.queueKey + ":high",
		q.queueKey + ":normal",
		q.queueKey + ":low",
	}

	var total int64
	for _, queue := range queues {
		length, err := q.client.LLen(q.ctx, queue).Result()
		if err != nil {
			return 0, fmt.Errorf("failed to get queue length: %w", err)
		}
		total += length
	}

	return total, nil
}

// GetTasksByStatus returns tasks with the specified status
func (q *TaskQueue) GetTasksByStatus(status string, limit int) ([]*Task, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()

	pattern := q.statusKey + "*"
	keys, err := q.client.Keys(q.ctx, pattern).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get task keys: %w", err)
	}

	var tasks []*Task
	for _, key := range keys {
		if len(tasks) >= limit {
			break
		}

		taskData, err := q.client.Get(q.ctx, key).Result()
		if err != nil {
			continue // Skip failed retrievals
		}

		var task Task
		err = json.Unmarshal([]byte(taskData), &task)
		if err != nil {
			continue // Skip failed deserializations
		}

		if task.Status == status {
			tasks = append(tasks, &task)
		}
	}

	return tasks, nil
}

// GetTasksByUser returns tasks for a specific user
func (q *TaskQueue) GetTasksByUser(userID string, limit int) ([]*Task, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()

	pattern := q.statusKey + "*"
	keys, err := q.client.Keys(q.ctx, pattern).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get task keys: %w", err)
	}

	var tasks []*Task
	for _, key := range keys {
		if len(tasks) >= limit {
			break
		}

		taskData, err := q.client.Get(q.ctx, key).Result()
		if err != nil {
			continue // Skip failed retrievals
		}

		var task Task
		err = json.Unmarshal([]byte(taskData), &task)
		if err != nil {
			continue // Skip failed deserializations
		}

		if task.UserID == userID {
			tasks = append(tasks, &task)
		}
	}

	return tasks, nil
}

// DeleteTask removes a task from the queue and status
func (q *TaskQueue) DeleteTask(taskID string) error {
	q.mu.Lock()
	defer q.mu.Unlock()

	statusKey := q.statusKey + taskID

	// Remove from status
	err := q.client.Del(q.ctx, statusKey).Err()
	if err != nil {
		return fmt.Errorf("failed to delete task status: %w", err)
	}

	// Remove from all priority queues (in case it's still pending)
	queues := []string{
		q.queueKey + ":high",
		q.queueKey + ":normal",
		q.queueKey + ":low",
	}

	for _, queue := range queues {
		q.client.LRem(q.ctx, queue, 0, taskID)
	}

	return nil
}

// PurgeCompletedTasks removes old completed tasks
func (q *TaskQueue) PurgeCompletedTasks(olderThan time.Duration) (int, error) {
	q.mu.Lock()
	defer q.mu.Unlock()

	pattern := q.statusKey + "*"
	keys, err := q.client.Keys(q.ctx, pattern).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to get task keys: %w", err)
	}

	cutoff := time.Now().Add(-olderThan)
	deleted := 0

	for _, key := range keys {
		taskData, err := q.client.Get(q.ctx, key).Result()
		if err != nil {
			continue
		}

		var task Task
		err = json.Unmarshal([]byte(taskData), &task)
		if err != nil {
			continue
		}

		if task.IsCompleted() && task.CompletedAt != nil && task.CompletedAt.Before(cutoff) {
			err = q.client.Del(q.ctx, key).Err()
			if err == nil {
				deleted++
			}
		}
	}

	if deleted > 0 {
		q.logger.Info("Purged completed tasks", zap.Int("count", deleted))
	}

	return deleted, nil
}

// GetQueueStats returns queue statistics
func (q *TaskQueue) GetQueueStats() (map[string]interface{}, error) {
	q.mu.RLock()
	defer q.mu.RUnlock()

	stats := make(map[string]interface{})

	// Get queue lengths
	queues := map[string]string{
		"high":   q.queueKey + ":high",
		"normal": q.queueKey + ":normal",
		"low":    q.queueKey + ":low",
	}

	queueLengths := make(map[string]int64)
	var totalPending int64

	for priority, queueKey := range queues {
		length, err := q.client.LLen(q.ctx, queueKey).Result()
		if err != nil {
			return nil, fmt.Errorf("failed to get queue length for %s: %w", priority, err)
		}
		queueLengths[priority] = length
		totalPending += length
	}

	// Count tasks by status
	pattern := q.statusKey + "*"
	keys, err := q.client.Keys(q.ctx, pattern).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get task keys: %w", err)
	}

	statusCounts := make(map[string]int)
	for _, key := range keys {
		taskData, err := q.client.Get(q.ctx, key).Result()
		if err != nil {
			continue
		}

		var task Task
		err = json.Unmarshal([]byte(taskData), &task)
		if err != nil {
			continue
		}

		statusCounts[task.Status]++
	}

	stats["queue_lengths"] = queueLengths
	stats["total_pending"] = totalPending
	stats["status_counts"] = statusCounts
	stats["total_tasks"] = len(keys)

	return stats, nil
}