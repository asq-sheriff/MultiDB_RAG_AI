package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap/zaptest"
)

var (
	testQueue           *TaskQueue
	testNotificationSvc *NotificationService
	testWorkerPool      *WorkerPool
	testApp             *gin.Engine
)

func TestMain(m *testing.M) {
	setup()
	code := m.Run()
	teardown()
	os.Exit(code)
}

func setup() {
	// Initialize test logger
	logger := zaptest.NewLogger(&testing.T{})

	// Initialize test Redis connections
	redisURL := os.Getenv("TEST_REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/2" // Use database 2 for tests
	}

	var err error

	// Initialize test task queue
	testQueue, err = NewTaskQueue(redisURL, logger)
	if err != nil {
		panic(fmt.Sprintf("Failed to connect to test Redis for queue: %v", err))
	}

	// Initialize test notification service
	testNotificationSvc, err = NewNotificationService(redisURL, logger)
	if err != nil {
		panic(fmt.Sprintf("Failed to connect to test Redis for notifications: %v", err))
	}

	// Initialize test worker pool (with 2 workers for testing)
	testWorkerPool = NewWorkerPool(2, testQueue, testNotificationSvc, logger)

	// Start worker pool
	testWorkerPool.Start()

	// Initialize test app
	gin.SetMode(gin.TestMode)
	handlers := NewBackgroundTaskHandlers(testQueue, testWorkerPool, testNotificationSvc, logger)
	
	config := Config{
		Environment:   "test",
		EnableMetrics: false,
	}
	
	testApp = setupRouter(handlers, logger, config)
}

func teardown() {
	if testWorkerPool != nil {
		testWorkerPool.Stop()
	}
	if testQueue != nil {
		testQueue.Close()
	}
	if testNotificationSvc != nil {
		testNotificationSvc.Close()
	}
}

func cleanupTestData() {
	// Clear Redis test database completely
	ctx := context.Background()
	testQueue.client.FlushDB(ctx)
	
	// Also clear any in-memory state
	if testWorkerPool != nil {
		// Stop and restart worker pool to clear any in-flight tasks
		testWorkerPool.Stop()
		testWorkerPool.Start()
	}
	
	// Give a moment for cleanup to complete
	time.Sleep(10 * time.Millisecond)
}

// Test Task Models
func TestTaskModels(t *testing.T) {
	cleanupTestData()

	userID := uuid.New().String()
	sessionID := uuid.New().String()
	
	data := map[string]interface{}{
		"data_description": "test data",
	}
	
	task := NewTask("data_analysis", userID, sessionID, data)
	
	assert.Equal(t, "data_analysis", task.Type)
	assert.Equal(t, userID, task.UserID)
	assert.Equal(t, sessionID, task.SessionID)
	assert.Equal(t, "pending", task.Status)
	assert.Equal(t, 2, task.Priority) // Default normal priority
	assert.Equal(t, 3, task.MaxRetries)
	assert.False(t, task.IsCompleted())
	assert.False(t, task.IsRunning())
	assert.False(t, task.CanRetry()) // Cannot retry when pending
}

func TestTaskStatusTransitions(t *testing.T) {
	task := NewTask("data_analysis", "user1", "session1", nil)
	
	// Initial state
	assert.Equal(t, "pending", task.Status)
	assert.Equal(t, 0.0, task.GetProgress())
	
	// Mark as started
	task.MarkStarted()
	assert.Equal(t, "running", task.Status)
	assert.True(t, task.IsRunning())
	assert.NotNil(t, task.StartedAt)
	assert.Greater(t, task.GetProgress(), 0.0)
	
	// Mark as completed
	result := map[string]string{"test": "result"}
	task.MarkCompleted(result)
	assert.Equal(t, "completed", task.Status)
	assert.True(t, task.IsCompleted())
	assert.Equal(t, 100.0, task.GetProgress())
	assert.Equal(t, result, task.Result)
	assert.Greater(t, task.DurationSeconds, 0.0)
}

func TestTaskFailureAndRetry(t *testing.T) {
	task := NewTask("data_analysis", "user1", "session1", nil)
	task.MarkStarted()
	
	// Mark as failed
	err := fmt.Errorf("test error")
	task.MarkFailed(err)
	assert.Equal(t, "failed", task.Status)
	assert.Equal(t, "test error", task.Error)
	assert.Equal(t, 1, task.RetryCount)
	assert.True(t, task.CanRetry())
	
	// Fail again
	task.MarkFailed(err)
	assert.Equal(t, 2, task.RetryCount)
	assert.True(t, task.CanRetry())
	
	// Fail third time
	task.MarkFailed(err)
	assert.Equal(t, 3, task.RetryCount)
	assert.False(t, task.CanRetry()) // Max retries reached
}

// Test Queue Operations
func TestTaskQueue(t *testing.T) {
	cleanupTestData()
	
	// Stop worker pool to prevent task consumption during tests
	testWorkerPool.Stop()
	defer testWorkerPool.Start()
	
	t.Run("EnqueueAndDequeue", func(t *testing.T) {
		task := NewTask("data_analysis", "user1", "session1", map[string]interface{}{
			"data_description": "test data",
		})
		
		// Enqueue task
		err := testQueue.Enqueue(task)
		require.NoError(t, err)
		
		// Check queue length
		length, err := testQueue.GetQueueLength()
		require.NoError(t, err)
		assert.Equal(t, int64(1), length)
		
		// Dequeue task
		dequeuedTask, err := testQueue.Dequeue(1 * time.Second)
		require.NoError(t, err)
		require.NotNil(t, dequeuedTask)
		assert.Equal(t, task.Type, dequeuedTask.Type)
		assert.Equal(t, task.UserID, dequeuedTask.UserID)
		assert.Equal(t, task.SessionID, dequeuedTask.SessionID)
		assert.NotEmpty(t, dequeuedTask.ID) // UUID should be present but we don't compare exact value
	})
	
	t.Run("PriorityQueue", func(t *testing.T) {
		// Create tasks with different priorities
		lowTask := NewTask("data_analysis", "user1", "session1", nil)
		lowTask.Priority = 3
		
		normalTask := NewTask("research", "user1", "session1", nil)
		normalTask.Priority = 2
		
		highTask := NewTask("data_analysis", "user1", "session1", nil)
		highTask.Priority = 1
		
		// Enqueue in random order
		err := testQueue.Enqueue(lowTask)
		require.NoError(t, err)
		err = testQueue.Enqueue(highTask)
		require.NoError(t, err)
		err = testQueue.Enqueue(normalTask)
		require.NoError(t, err)
		
		// Dequeue should return highest priority first
		task1, err := testQueue.Dequeue(1 * time.Second)
		require.NoError(t, err)
		require.NotNil(t, task1)
		assert.Equal(t, highTask.Priority, task1.Priority)
		assert.Equal(t, highTask.Type, task1.Type)
		
		task2, err := testQueue.Dequeue(1 * time.Second)
		require.NoError(t, err)
		require.NotNil(t, task2)
		assert.Equal(t, normalTask.Priority, task2.Priority)
		assert.Equal(t, normalTask.Type, task2.Type)
		
		task3, err := testQueue.Dequeue(1 * time.Second)
		require.NoError(t, err)
		require.NotNil(t, task3)
		assert.Equal(t, lowTask.Priority, task3.Priority)
		assert.Equal(t, lowTask.Type, task3.Type)
	})
}

func TestTaskStatusOperations(t *testing.T) {
	cleanupTestData()
	
	task := NewTask("data_analysis", "user1", "session1", nil)
	
	// Store task status
	err := testQueue.UpdateTaskStatus(task)
	require.NoError(t, err)
	
	// Retrieve task status
	retrievedTask, err := testQueue.GetTaskStatus(task.ID)
	require.NoError(t, err)
	require.NotNil(t, retrievedTask)
	assert.Equal(t, task.ID, retrievedTask.ID)
	assert.Equal(t, task.Status, retrievedTask.Status)
	
	// Update task status
	task.MarkStarted()
	err = testQueue.UpdateTaskStatus(task)
	require.NoError(t, err)
	
	// Verify update
	updatedTask, err := testQueue.GetTaskStatus(task.ID)
	require.NoError(t, err)
	assert.Equal(t, "running", updatedTask.Status)
}

// Test API Endpoints
func TestHealthCheck(t *testing.T) {
	cleanupTestData()
	
	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response HealthCheckResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	// Status should be "degraded" when no workers are busy processing tasks
	assert.Equal(t, "degraded", response.Status)
	assert.Equal(t, "background-tasks-service-go", response.Service)
}

func TestSubmitTask(t *testing.T) {
	cleanupTestData()
	
	requestBody := TaskSubmissionRequest{
		Type:      "data_analysis",
		UserID:    "test-user",
		SessionID: "test-session",
		Data: map[string]interface{}{
			"data_description": "Test analysis data",
		},
		Priority: 1,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", "/api/v1/tasks", bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusAccepted, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Task submitted successfully", response.Message)
	
	// Verify response data
	responseData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, responseData, "task_id")
	assert.Equal(t, "pending", responseData["status"])
	assert.Equal(t, float64(1), responseData["priority"])
}

func TestSubmitInvalidTask(t *testing.T) {
	cleanupTestData()
	
	// Invalid task type
	requestBody := TaskSubmissionRequest{
		Type:      "invalid_type",
		UserID:    "test-user",
		SessionID: "test-session",
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", "/api/v1/tasks", bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.False(t, response.Success)
	assert.Contains(t, response.Error, "Invalid task type")
}

func TestSubmitDataAnalysisTask(t *testing.T) {
	cleanupTestData()
	
	requestBody := map[string]interface{}{
		"user_id":          "test-user",
		"session_id":       "test-session",
		"data_description": "Large dataset analysis",
		"priority":         2,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", "/api/v1/tasks/data-analysis", bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusAccepted, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
}

func TestSubmitResearchTask(t *testing.T) {
	cleanupTestData()
	
	requestBody := map[string]interface{}{
		"user_id":        "test-user",
		"session_id":     "test-session",
		"research_topic": "AI developments",
		"priority":       1,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", "/api/v1/tasks/research", bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusAccepted, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
}

func TestGetTaskStatus(t *testing.T) {
	cleanupTestData()
	
	// Create and store a task
	task := NewTask("data_analysis", "test-user", "test-session", map[string]interface{}{
		"data_description": "test data",
	})
	err := testQueue.UpdateTaskStatus(task)
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/tasks/%s", task.ID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify response data
	responseData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, task.ID, responseData["task_id"])
	assert.Equal(t, "pending", responseData["status"])
}

func TestGetNonexistentTaskStatus(t *testing.T) {
	cleanupTestData()
	
	nonexistentID := uuid.New().String()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/tasks/%s", nonexistentID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusNotFound, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.False(t, response.Success)
	assert.Equal(t, "Task not found", response.Error)
}

func TestGetServiceStats(t *testing.T) {
	cleanupTestData()
	
	req, _ := http.NewRequest("GET", "/api/v1/stats", nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify response structure
	responseData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, responseData, "active_workers")
	assert.Contains(t, responseData, "total_tasks")
	assert.Contains(t, responseData, "workers")
}

func TestGetWorkerStats(t *testing.T) {
	cleanupTestData()
	
	req, _ := http.NewRequest("GET", "/api/v1/workers", nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify workers array
	workers, ok := response.Data.([]interface{})
	require.True(t, ok)
	assert.Len(t, workers, 2) // We initialized 2 workers
}

// Test Notifications
func TestNotificationOperations(t *testing.T) {
	cleanupTestData()
	
	userID := "test-user"
	
	// Test getting notifications (should be empty initially)
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/notifications", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	responseData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	notifications, ok := responseData["notifications"].([]interface{})
	require.True(t, ok)
	assert.Len(t, notifications, 0)
}

func TestClearNotifications(t *testing.T) {
	cleanupTestData()
	
	userID := "test-user"
	
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/api/v1/users/%s/notifications", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Notifications cleared successfully", response.Message)
}

// Integration Tests
func TestTaskProcessingIntegration(t *testing.T) {
	cleanupTestData()
	
	// Submit a data analysis task
	requestBody := TaskSubmissionRequest{
		Type:      "data_analysis",
		UserID:    "integration-test-user",
		SessionID: "integration-test-session",
		Data: map[string]interface{}{
			"data_description": "Integration test data",
		},
		Priority: 1,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", "/api/v1/tasks", bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	require.Equal(t, http.StatusAccepted, w.Code)
	
	var submitResponse APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &submitResponse)
	require.NoError(t, err)
	
	responseData, ok := submitResponse.Data.(map[string]interface{})
	require.True(t, ok)
	taskID := responseData["task_id"].(string)
	
	// Wait for task to be processed (up to 5 seconds)
	var task *Task
	for i := 0; i < 50; i++ {
		time.Sleep(100 * time.Millisecond)
		task, err = testQueue.GetTaskStatus(taskID)
		require.NoError(t, err)
		if task != nil && task.IsCompleted() {
			break
		}
	}
	
	// Verify task completion
	require.NotNil(t, task)
	assert.Equal(t, "completed", task.Status)
	assert.NotNil(t, task.Result)
	
	// Verify result structure for data analysis
	result, ok := task.Result.(map[string]interface{})
	if ok {
		assert.Contains(t, result, "summary")
		assert.Contains(t, result, "insights")
	}
	
	// Check that notification was sent
	time.Sleep(500 * time.Millisecond) // Allow time for notification processing
	
	notifReq, _ := http.NewRequest("GET", "/api/v1/users/integration-test-user/notifications?limit=5", nil)
	notifW := httptest.NewRecorder()
	testApp.ServeHTTP(notifW, notifReq)
	
	assert.Equal(t, http.StatusOK, notifW.Code)
	
	var notifResponse APIResponse
	err = json.Unmarshal(notifW.Body.Bytes(), &notifResponse)
	require.NoError(t, err)
	
	notifData, ok := notifResponse.Data.(map[string]interface{})
	require.True(t, ok)
	notifications, ok := notifData["notifications"].([]interface{})
	require.True(t, ok)
	
	// Should have at least one notification
	assert.GreaterOrEqual(t, len(notifications), 1)
}

// Benchmark Tests
func BenchmarkTaskSubmission(b *testing.B) {
	cleanupTestData()
	
	requestBody := TaskSubmissionRequest{
		Type:      "data_analysis",
		UserID:    "bench-user",
		SessionID: "bench-session",
		Data: map[string]interface{}{
			"data_description": "Benchmark data",
		},
		Priority: 2,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", "/api/v1/tasks", bytes.NewBuffer(requestJSON))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		if w.Code != http.StatusAccepted {
			b.Fatalf("Expected status 202, got %d", w.Code)
		}
	}
}

func BenchmarkTaskStatusCheck(b *testing.B) {
	cleanupTestData()
	
	// Create a test task
	task := NewTask("data_analysis", "bench-user", "bench-session", nil)
	err := testQueue.UpdateTaskStatus(task)
	require.NoError(b, err)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/tasks/%s", task.ID), nil)
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		if w.Code != http.StatusOK {
			b.Fatalf("Expected status 200, got %d", w.Code)
		}
	}
}