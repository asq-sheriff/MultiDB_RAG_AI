"""Background task processing service for long-running operations."""

import time
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future

from app.database.redis_models import NotificationModel, AnalyticsModel

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a background task"""

    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class BackgroundTaskService:
    """Service for handling long-running background tasks."""

    def __init__(self):
        self.notification_model = NotificationModel()
        self.analytics_model = AnalyticsModel()

        # Simple thread pool - let Python handle threading automatically
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="bg_task")

        # Track running tasks
        self._running_tasks: Dict[str, Future] = {}

    def submit_data_analysis_task(
        self, user_id: str, data_description: str, session_id: str
    ) -> str:
        """Submit a data analysis task for background processing."""
        task_id = str(uuid.uuid4())

        # Submit task to thread pool
        future = self.executor.submit(
            self._process_data_analysis, task_id, user_id, data_description, session_id
        )

        # Track the task
        self._running_tasks[task_id] = future

        # Record analytics
        self.analytics_model.increment_counter("background_tasks_submitted")
        self.analytics_model.record_event(
            "task_submitted",
            {
                "task_id": task_id,
                "task_type": "data_analysis",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"📋 Submitted data analysis task {task_id} for user {user_id}")
        return task_id

    def submit_research_task(
        self, user_id: str, research_topic: str, session_id: str
    ) -> str:
        """Submit a research task for background processing."""
        task_id = str(uuid.uuid4())

        # Submit task to thread pool
        future = self.executor.submit(
            self._process_research_task, task_id, user_id, research_topic, session_id
        )

        # Track the task
        self._running_tasks[task_id] = future

        # Record analytics
        self.analytics_model.increment_counter("background_tasks_submitted")
        self.analytics_model.record_event(
            "task_submitted",
            {
                "task_id": task_id,
                "task_type": "research",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"🔍 Submitted research task {task_id} for user {user_id}")
        return task_id

    def _process_data_analysis(
        self, task_id: str, user_id: str, data_description: str, session_id: str
    ) -> TaskResult:
        """
        Process data analysis task (simulated long-running operation).
        Runs in background thread.

        Args:
            task_id: Task identifier
            user_id: User identifier
            data_description: Data to analyze
            session_id: Chat session

        Returns:
            TaskResult: Result of the analysis
        """
        start_time = time.time()

        try:
            logger.info(f"🚀 Starting data analysis task {task_id}")

            # Simulate different processing times - SHORTENED FOR TESTING
            if "large" in data_description.lower():
                processing_time = 2  # Was 15 seconds
            elif "complex" in data_description.lower():
                processing_time = 1  # Was 10 seconds
            else:
                processing_time = 1  # Was 5 seconds

            # Simulate processing steps
            steps = ["Loading data", "Preprocessing", "Analysis", "Generating report"]
            for i, step in enumerate(steps):
                time.sleep(processing_time / len(steps))
                logger.debug(f"Task {task_id}: {step} ({i + 1}/{len(steps)})")

            # Generate mock analysis result
            analysis_result = {
                "summary": f"Analysis of '{data_description}' completed successfully",
                "insights": [
                    "Data shows clear trends and patterns",
                    "Identified 3 key areas for improvement",
                    "Correlation strength: 0.85",
                    "Recommended next steps: Further investigation needed",
                ],
                "charts_generated": 2,
                "recommendations": "Consider expanding dataset for deeper insights",
            }

            duration = time.time() - start_time

            # Send completion notification
            self._send_completion_notification(
                user_id=user_id,
                task_id=task_id,
                task_type="Data Analysis",
                result=analysis_result,
                duration=duration,
            )

            return TaskResult(
                task_id=task_id,
                success=True,
                result=analysis_result,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Data analysis failed: {str(e)}"

            # Send error notification
            self._send_error_notification(
                user_id=user_id,
                task_id=task_id,
                task_type="Data Analysis",
                error=error_msg,
                duration=duration,
            )

            return TaskResult(
                task_id=task_id,
                success=False,
                error=error_msg,
                duration_seconds=duration,
            )

        finally:
            # Clean up task tracking
            self._running_tasks.pop(task_id, None)

    def _process_research_task(
        self, task_id: str, user_id: str, research_topic: str, session_id: str
    ) -> TaskResult:
        """
        Process research task (simulated long-running operation).
        Runs in background thread.
        """
        start_time = time.time()

        try:
            logger.info(
                f"🔍 Starting research task {task_id} on topic: {research_topic}"
            )

            # Simulate research steps - SHORTENED FOR TESTING
            steps = [
                "Searching academic databases",
                "Analyzing sources",
                "Cross-referencing information",
                "Compiling findings",
            ]

            for i, step in enumerate(steps):
                time.sleep(0.25)  # Was 2 seconds, now 0.25 seconds
                logger.debug(f"Task {task_id}: {step} ({i + 1}/{len(steps)})")

            # Generate mock research result
            research_result = {
                "topic": research_topic,
                "summary": f"Comprehensive research on '{research_topic}' completed",
                "sources_found": 15,
                "key_findings": [
                    f"Latest developments in {research_topic}",
                    "Industry trends and future outlook",
                    "Best practices and recommendations",
                ],
                "research_date": datetime.now(timezone.utc).isoformat(),
                "confidence_level": "High",
            }

            duration = time.time() - start_time

            # Send completion notification
            self._send_completion_notification(
                user_id=user_id,
                task_id=task_id,
                task_type="Research",
                result=research_result,
                duration=duration,
            )

            return TaskResult(
                task_id=task_id,
                success=True,
                result=research_result,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Research failed: {str(e)}"

            # Send error notification
            self._send_error_notification(
                user_id=user_id,
                task_id=task_id,
                task_type="Research",
                error=error_msg,
                duration=duration,
            )

            return TaskResult(
                task_id=task_id,
                success=False,
                error=error_msg,
                duration_seconds=duration,
            )

        finally:
            # Clean up task tracking
            self._running_tasks.pop(task_id, None)

    def _send_completion_notification(
        self,
        user_id: str,
        task_id: str,
        task_type: str,
        result: Dict[str, Any],
        duration: float,
    ) -> None:
        """Send task completion notification with detailed results"""

        # Create rich notification with actual results
        if task_type == "Data Analysis":
            detailed_message = f"""📊 **{task_type} Complete!** ({duration:.1f}s)

**Summary**: {result.get("summary", "Analysis completed successfully")}

**Key Insights**:
{chr(10).join(f"• {insight}" for insight in result.get("insights", ["Results generated successfully"]))}

**Charts Generated**: {result.get("charts_generated", "N/A")}
**Recommendations**: {result.get("recommendations", "See detailed results above")}

🆔 Task ID: {task_id[:8]}..."""

        else:  # Research task
            detailed_message = f"""🔍 **{task_type} Complete!** ({duration:.1f}s)

**Topic**: {result.get("topic", "Research completed")}
**Summary**: {result.get("summary", "Research completed successfully")}

**Sources Found**: {result.get("sources_found", "Multiple sources")}

**Key Findings**:
{chr(10).join(f"• {finding}" for finding in result.get("key_findings", ["Research completed successfully"]))}

**Confidence Level**: {result.get("confidence_level", "High")}

🆔 Task ID: {task_id[:8]}..."""

        notification = {
            "type": "success",
            "title": f"{task_type} Complete! ✅",
            "message": detailed_message,
            "data": {
                "task_id": task_id,
                "task_type": task_type.lower(),
                "duration_seconds": duration,
                "result_summary": result.get("summary", "Task completed successfully"),
                "full_results": result,  # Include full results
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Add to user's notification queue
        success = self.notification_model.add_notification(user_id, notification)

        if success:
            logger.info(
                f"✅ Detailed notification sent to user {user_id} for task {task_id}"
            )
        else:
            logger.error(f"❌ Failed to send notification to user {user_id}")

        # Record analytics
        self.analytics_model.increment_counter("notifications_sent")
        self.analytics_model.record_event(
            "task_completed",
            {
                "task_id": task_id,
                "task_type": task_type.lower(),
                "user_id": user_id,
                "duration_seconds": duration,
                "success": True,
            },
        )

    def _send_error_notification(
        self, user_id: str, task_id: str, task_type: str, error: str, duration: float
    ) -> None:
        """Send task error notification using Redis Lists"""

        notification = {
            "type": "error",
            "title": f"{task_type} Failed ❌",
            "message": f"Your {task_type.lower()} task encountered an error after {duration:.1f} seconds.",
            "data": {
                "task_id": task_id,
                "task_type": task_type.lower(),
                "duration_seconds": duration,
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Add to user's notification queue
        success = self.notification_model.add_notification(user_id, notification)

        if success:
            logger.info(
                f"❌ Error notification sent to user {user_id} for task {task_id}"
            )
        else:
            logger.error(f"❌ Failed to send error notification to user {user_id}")

        # Record analytics
        self.analytics_model.increment_counter("notifications_sent")
        self.analytics_model.record_event(
            "task_failed",
            {
                "task_id": task_id,
                "task_type": task_type.lower(),
                "user_id": user_id,
                "duration_seconds": duration,
                "error": error,
                "success": False,
            },
        )

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a running task.
        Called by: ChatbotService for task status checks
        """
        if task_id in self._running_tasks:
            future = self._running_tasks[task_id]

            if future.running():
                return {"status": "running", "task_id": task_id}
            elif future.done():
                try:
                    result = future.result()
                    return {
                        "status": "completed",
                        "task_id": task_id,
                        "success": result.success,
                        "duration": result.duration_seconds,
                    }
                except Exception as e:
                    return {"status": "failed", "task_id": task_id, "error": str(e)}

        return {"status": "not_found", "task_id": task_id}

    def shutdown(self):
        """Cleanup background task service - force immediate shutdown"""
        logger.info("Shutting down background task service...")
        try:
            # Cancel all running futures immediately
            for task_id, future in list(self._running_tasks.items()):
                try:
                    future.cancel()
                    logger.debug(f"Cancelled task: {task_id}")
                except Exception as e:
                    logger.debug(f"Error cancelling task {task_id}: {e}")

            # Clear tracking
            self._running_tasks.clear()

            # Force immediate shutdown without waiting
            self.executor.shutdown(wait=False)

            logger.info("Background task service shutdown complete")
        except Exception as e:
            logger.error(f"Error during background task shutdown: {e}")
            # Force shutdown anyway
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass
