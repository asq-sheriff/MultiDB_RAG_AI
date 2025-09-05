package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// NotificationService handles sending notifications to users
type NotificationService struct {
	client     *redis.Client
	logger     *zap.Logger
	ctx        context.Context
	analytics  *AnalyticsService
}

// AnalyticsService handles analytics tracking
type AnalyticsService struct {
	client *redis.Client
	logger *zap.Logger
	ctx    context.Context
}

// NewNotificationService creates a new notification service
func NewNotificationService(redisURL string, logger *zap.Logger) (*NotificationService, error) {
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

	analytics := &AnalyticsService{
		client: client,
		logger: logger.With(zap.String("component", "analytics")),
		ctx:    ctx,
	}

	return &NotificationService{
		client:    client,
		logger:    logger.With(zap.String("component", "notifications")),
		ctx:       ctx,
		analytics: analytics,
	}, nil
}

// Close closes the Redis connection
func (n *NotificationService) Close() error {
	return n.client.Close()
}

// SendCompletionNotification sends a task completion notification
func (n *NotificationService) SendCompletionNotification(task *Task, result interface{}) error {
	var detailedMessage string
	
	switch task.Type {
	case "data_analysis":
		if analysisResult, ok := result.(DataAnalysisResult); ok {
			detailedMessage = fmt.Sprintf(`📊 **Data Analysis Complete!** (%.1fs)

**Summary**: %s

**Key Insights**:
%s

**Charts Generated**: %d
**Recommendations**: %s

🆔 Task ID: %s...`, 
				task.DurationSeconds,
				analysisResult.Summary,
				formatInsights(analysisResult.Insights),
				analysisResult.ChartsGenerated,
				analysisResult.Recommendations,
				task.ID[:8])
		} else {
			detailedMessage = fmt.Sprintf("📊 **Data Analysis Complete!** (%.1fs)\n\n🆔 Task ID: %s...", 
				task.DurationSeconds, task.ID[:8])
		}
		
	case "research":
		if researchResult, ok := result.(ResearchResult); ok {
			detailedMessage = fmt.Sprintf(`🔍 **Research Complete!** (%.1fs)

**Topic**: %s
**Summary**: %s

**Sources Found**: %d

**Key Findings**:
%s

**Confidence Level**: %s

🆔 Task ID: %s...`,
				task.DurationSeconds,
				researchResult.Topic,
				researchResult.Summary,
				researchResult.SourcesFound,
				formatFindings(researchResult.KeyFindings),
				researchResult.ConfidenceLevel,
				task.ID[:8])
		} else {
			detailedMessage = fmt.Sprintf("🔍 **Research Complete!** (%.1fs)\n\n🆔 Task ID: %s...", 
				task.DurationSeconds, task.ID[:8])
		}
		
	default:
		detailedMessage = fmt.Sprintf("✅ **Task Complete!** (%.1fs)\n\n🆔 Task ID: %s...", 
			task.DurationSeconds, task.ID[:8])
	}

	notification := Notification{
		Type:    "success",
		Title:   fmt.Sprintf("%s Complete! ✅", capitalizeTaskType(task.Type)),
		Message: detailedMessage,
		Data: map[string]interface{}{
			"task_id":           task.ID,
			"task_type":         task.Type,
			"duration_seconds":  task.DurationSeconds,
			"result_summary":    getResultSummary(result),
			"full_results":      result,
			"completed_at":      task.CompletedAt.Format(time.RFC3339),
		},
	}

	// Send notification
	err := n.addNotification(task.UserID, notification)
	if err != nil {
		n.logger.Error("Failed to send completion notification", 
			zap.String("task_id", task.ID),
			zap.String("user_id", task.UserID),
			zap.Error(err))
		return err
	}

	// Record analytics
	n.analytics.IncrementCounter("notifications_sent")
	n.analytics.RecordEvent("task_completed", map[string]interface{}{
		"task_id":          task.ID,
		"task_type":        task.Type,
		"user_id":          task.UserID,
		"duration_seconds": task.DurationSeconds,
		"success":          true,
		"timestamp":        time.Now().Format(time.RFC3339),
	})

	n.logger.Info("Completion notification sent", 
		zap.String("task_id", task.ID),
		zap.String("user_id", task.UserID))

	return nil
}

// SendErrorNotification sends a task error notification
func (n *NotificationService) SendErrorNotification(task *Task, errorMsg string) error {
	notification := Notification{
		Type:    "error",
		Title:   fmt.Sprintf("%s Failed ❌", capitalizeTaskType(task.Type)),
		Message: fmt.Sprintf("Your %s task encountered an error after %.1f seconds.\n\n🆔 Task ID: %s...", 
			task.Type, task.DurationSeconds, task.ID[:8]),
		Data: map[string]interface{}{
			"task_id":          task.ID,
			"task_type":        task.Type,
			"duration_seconds": task.DurationSeconds,
			"error":            errorMsg,
			"failed_at":        task.CompletedAt.Format(time.RFC3339),
		},
	}

	// Send notification
	err := n.addNotification(task.UserID, notification)
	if err != nil {
		n.logger.Error("Failed to send error notification", 
			zap.String("task_id", task.ID),
			zap.String("user_id", task.UserID),
			zap.Error(err))
		return err
	}

	// Record analytics
	n.analytics.IncrementCounter("notifications_sent")
	n.analytics.RecordEvent("task_failed", map[string]interface{}{
		"task_id":          task.ID,
		"task_type":        task.Type,
		"user_id":          task.UserID,
		"duration_seconds": task.DurationSeconds,
		"error":            errorMsg,
		"success":          false,
		"timestamp":        time.Now().Format(time.RFC3339),
	})

	n.logger.Info("Error notification sent", 
		zap.String("task_id", task.ID),
		zap.String("user_id", task.UserID))

	return nil
}

// addNotification adds a notification to a user's queue
func (n *NotificationService) addNotification(userID string, notification Notification) error {
	notificationKey := fmt.Sprintf("notifications:%s", userID)
	
	// Serialize notification
	notificationData, err := json.Marshal(notification)
	if err != nil {
		return fmt.Errorf("failed to marshal notification: %w", err)
	}

	// Add to user's notification list (FIFO queue)
	err = n.client.LPush(n.ctx, notificationKey, notificationData).Err()
	if err != nil {
		return fmt.Errorf("failed to add notification: %w", err)
	}

	// Set expiration on the list (24 hours)
	n.client.Expire(n.ctx, notificationKey, 24*time.Hour)

	// Trim list to keep only last 50 notifications
	n.client.LTrim(n.ctx, notificationKey, 0, 49)

	return nil
}

// GetNotifications retrieves notifications for a user
func (n *NotificationService) GetNotifications(userID string, limit int) ([]Notification, error) {
	notificationKey := fmt.Sprintf("notifications:%s", userID)
	
	// Get notifications (most recent first)
	results, err := n.client.LRange(n.ctx, notificationKey, 0, int64(limit-1)).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get notifications: %w", err)
	}

	notifications := make([]Notification, 0, len(results))
	for _, result := range results {
		var notification Notification
		err := json.Unmarshal([]byte(result), &notification)
		if err != nil {
			n.logger.Error("Failed to unmarshal notification", zap.Error(err))
			continue
		}
		notifications = append(notifications, notification)
	}

	return notifications, nil
}

// ClearNotifications clears all notifications for a user
func (n *NotificationService) ClearNotifications(userID string) error {
	notificationKey := fmt.Sprintf("notifications:%s", userID)
	
	err := n.client.Del(n.ctx, notificationKey).Err()
	if err != nil {
		return fmt.Errorf("failed to clear notifications: %w", err)
	}

	return nil
}

// IncrementCounter increments an analytics counter
func (a *AnalyticsService) IncrementCounter(counter string) error {
	key := fmt.Sprintf("analytics:counters:%s", counter)
	err := a.client.Incr(a.ctx, key).Err()
	if err != nil {
		a.logger.Error("Failed to increment counter", zap.String("counter", counter), zap.Error(err))
		return err
	}
	return nil
}

// RecordEvent records an analytics event
func (a *AnalyticsService) RecordEvent(eventType string, data map[string]interface{}) error {
	event := map[string]interface{}{
		"event_type": eventType,
		"timestamp":  time.Now().Format(time.RFC3339),
		"data":       data,
	}

	eventData, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	// Store in time-series list
	key := fmt.Sprintf("analytics:events:%s", eventType)
	err = a.client.LPush(a.ctx, key, eventData).Err()
	if err != nil {
		a.logger.Error("Failed to record event", zap.String("event_type", eventType), zap.Error(err))
		return err
	}

	// Set expiration and trim list
	a.client.Expire(a.ctx, key, 7*24*time.Hour) // Keep events for 7 days
	a.client.LTrim(a.ctx, key, 0, 999)          // Keep last 1000 events

	return nil
}

// GetCounters gets analytics counters
func (a *AnalyticsService) GetCounters() (map[string]int64, error) {
	pattern := "analytics:counters:*"
	keys, err := a.client.Keys(a.ctx, pattern).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get counter keys: %w", err)
	}

	counters := make(map[string]int64)
	for _, key := range keys {
		// Extract counter name from key
		counterName := key[len("analytics:counters:"):]
		
		value, err := a.client.Get(a.ctx, key).Int64()
		if err != nil {
			continue // Skip failed retrievals
		}
		
		counters[counterName] = value
	}

	return counters, nil
}

// Helper functions
func capitalizeTaskType(taskType string) string {
	switch taskType {
	case "data_analysis":
		return "Data Analysis"
	case "research":
		return "Research"
	default:
		return "Task"
	}
}

func formatInsights(insights []string) string {
	result := ""
	for _, insight := range insights {
		result += "• " + insight + "\n"
	}
	return result
}

func formatFindings(findings []string) string {
	result := ""
	for _, finding := range findings {
		result += "• " + finding + "\n"
	}
	return result
}

func getResultSummary(result interface{}) string {
	switch r := result.(type) {
	case DataAnalysisResult:
		return r.Summary
	case ResearchResult:
		return r.Summary
	default:
		return "Task completed successfully"
	}
}