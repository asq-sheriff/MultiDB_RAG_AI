"""Timeout-based processor that automatically moves long-running tasks to background."""

import time
import logging
from typing import Callable, Any, Optional, Dict, TYPE_CHECKING
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import uuid

if TYPE_CHECKING:
    from app.services.background_tasks import BackgroundTaskService

logger = logging.getLogger(__name__)


@dataclass
class TimeoutConfig:
    """Configuration for timeout processing"""

    timeout_threshold_seconds: float = 5.0  # When to move to background
    check_interval_seconds: float = 1.0  # How often to check
    max_foreground_duration: float = 10.0  # Absolute max foreground time


class TimeoutProcessor:
    """Processes requests with automatic timeout detection."""

    def __init__(self, background_service: Optional["BackgroundTaskService"] = None):
        self.background_service = background_service
        self.config = TimeoutConfig()

        # Track active foreground tasks
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="timeout_proc"
        )

    def process_with_timeout(
        self,
        task_function: Callable,
        timeout_threshold: float,
        session_id: str,
        user_id: str,
        user_message: str,
        task_type: str = "analysis",
    ) -> Any:
        """
        Process a task with automatic timeout detection.

        Args:
            task_function: Function to execute (should be the actual processing logic)
            timeout_threshold: Seconds before moving to background
            session_id: Current session ID
            user_id: User identifier
            user_message: Original user message
            task_type: Type of task ("analysis" or "research")

        Returns:
            Either the result (if completed quickly) or a timeout response
        """
        task_id = str(uuid.uuid4())

        logger.info(
            f"Starting timeout-monitored task {task_id} with {timeout_threshold}s threshold"
        )

        # Store task info for monitoring
        self._active_tasks[task_id] = {
            "start_time": time.time(),
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "task_type": task_type,
            "threshold": timeout_threshold,
            "status": "running",
        }

        try:
            # Submit task to executor
            future = self._executor.submit(task_function)

            # Monitor for timeout
            start_time = time.time()

            while not future.done():
                elapsed = time.time() - start_time

                # Check if we've exceeded threshold
                if elapsed >= timeout_threshold:
                    logger.info(
                        f"Task {task_id} exceeded threshold ({elapsed:.1f}s), moving to background"
                    )

                    # Cancel the future (though it may continue running)
                    future.cancel()

                    # Move to background processing
                    background_task_id = self._move_to_background(
                        task_id, session_id, user_id, user_message, task_type
                    )

                    # Return timeout response
                    return self._create_timeout_response(background_task_id, elapsed)

                # Check if we've hit absolute maximum
                if elapsed >= self.config.max_foreground_duration:
                    logger.warning(
                        f"Task {task_id} hit absolute maximum ({elapsed:.1f}s), forcing background"
                    )
                    future.cancel()
                    background_task_id = self._move_to_background(
                        task_id, session_id, user_id, user_message, task_type
                    )
                    return self._create_timeout_response(
                        background_task_id, elapsed, forced=True
                    )

                # Sleep briefly before next check
                time.sleep(self.config.check_interval_seconds)

            # Task completed within threshold
            result = future.result()
            completion_time = time.time() - start_time

            logger.info(
                f"Task {task_id} completed in foreground ({completion_time:.1f}s)"
            )
            self._active_tasks[task_id]["status"] = "completed"

            return result

        except Exception as e:
            logger.error(f"Error in timeout processor for task {task_id}: {e}")
            self._active_tasks[task_id]["status"] = "error"
            raise

        finally:
            # Cleanup task tracking
            self._active_tasks.pop(task_id, None)

    def _move_to_background(
        self,
        task_id: str,
        session_id: str,
        user_id: str,
        user_message: str,
        task_type: str,
    ) -> str:
        """
        Move a task to background processing.

        Returns:
            str: Background task ID
        """
        try:
            if task_type == "analysis":
                # Extract analysis description from user message
                description = self._extract_analysis_description(user_message)
                background_task_id = self.background_service.submit_data_analysis_task(
                    user_id=user_id, data_description=description, session_id=session_id
                )
            else:  # research
                # Extract research topic from user message
                topic = self._extract_research_topic(user_message)
                background_task_id = self.background_service.submit_research_task(
                    user_id=user_id, research_topic=topic, session_id=session_id
                )

            logger.info(
                f"Successfully moved task {task_id} to background as {background_task_id}"
            )
            return background_task_id

        except Exception as e:
            logger.error(f"Failed to move task {task_id} to background: {e}")
            return f"timeout_{task_id}"  # Fallback ID

    def _extract_analysis_description(self, user_message: str) -> str:
        """Extract analysis description from user message"""
        # Remove common prefixes and clean up the message
        message = user_message.lower().strip()

        # Remove common request prefixes
        prefixes_to_remove = [
            "can you",
            "please",
            "i need",
            "help me",
            "could you",
            "analyze",
            "analysis",
            "do an analysis of",
            "perform analysis on",
        ]

        for prefix in prefixes_to_remove:
            if message.startswith(prefix):
                message = message[len(prefix) :].strip()

        # Ensure it's descriptive enough
        if len(message) < 10:
            return f"data analysis: {user_message}"

        return message

    def _extract_research_topic(self, user_message: str) -> str:
        """Extract research topic from user message"""
        message = user_message.lower().strip()

        # Remove research-specific prefixes
        prefixes_to_remove = [
            "research",
            "investigate",
            "look up",
            "find information about",
            "tell me about",
            "learn about",
            "study",
        ]

        for prefix in prefixes_to_remove:
            if message.startswith(prefix):
                message = message[len(prefix) :].strip()

        if len(message) < 5:
            return f"research: {user_message}"

        return message

    def _create_timeout_response(
        self, background_task_id: str, elapsed_time: float, forced: bool = False
    ) -> Dict[str, Any]:
        """Create response object for timeout scenarios"""

        if forced:
            message = f"""⏱️ **Processing Time Exceeded**

Your request is taking longer than expected ({elapsed_time:.1f} seconds). I've automatically moved it to background processing to keep our conversation flowing smoothly.

🆔 **Background Task ID**: {background_task_id[:8]}...
🔔 **Notification**: You'll receive an alert when it's complete
💬 **Continue**: Feel free to ask other questions while I work on this

💡 Type '/notifications' to check for updates"""
        else:
            message = f"""⏱️ **Moved to Background Processing**

This request is taking a bit longer than usual ({elapsed_time:.1f} seconds), so I've moved it to background processing.

🆔 **Task ID**: {background_task_id[:8]}...
🔔 **Notification**: I'll notify you as soon as it's complete
💬 **Continue**: You can continue our conversation normally

💡 Type '/notifications' to check progress"""

        # Return a response object that looks like a normal ChatResponse
        return {
            "message": message,
            "timeout_transferred": True,
            "background_task_id": background_task_id,
            "elapsed_time": elapsed_time,
            "has_context": True,
            "session_info": {
                "command_type": "timeout_transfer",
                "task_id": background_task_id,
                "transfer_reason": "forced" if forced else "threshold",
            },
        }

    def get_active_task_count(self) -> int:
        """Get count of currently active tasks"""
        return len(
            [
                task
                for task in self._active_tasks.values()
                if task["status"] == "running"
            ]
        )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        return self._active_tasks.get(task_id)

    def shutdown(self):
        """Shutdown the timeout processor"""
        logger.info("Shutting down timeout processor...")
        self._executor.shutdown(wait=True)
        self._active_tasks.clear()
        logger.info("Timeout processor shutdown complete")
