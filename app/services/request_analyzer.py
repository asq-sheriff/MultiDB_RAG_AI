"""Intelligent request analyzer for automatic background task detection."""

import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels"""

    SIMPLE = "simple"  # < 2 seconds expected
    MODERATE = "moderate"  # 2-10 seconds expected
    COMPLEX = "complex"  # 10-30 seconds expected
    HEAVY = "heavy"  # > 30 seconds expected


@dataclass
class RequestAnalysis:
    """Analysis result for a user request"""

    complexity: TaskComplexity
    estimated_duration_seconds: int
    should_background: bool
    detected_keywords: List[str]
    task_type: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


class RequestAnalyzer:
    """Analyzes user requests to determine processing complexity."""

    def __init__(self):
        # Define keyword patterns that indicate complex operations
        self.complexity_patterns = {
            # Heavy operations (>30 seconds)
            TaskComplexity.HEAVY: {
                "keywords": [
                    "full report",
                    "complete analysis",
                    "comprehensive report",
                    "entire database",
                    "all records",
                    "full history",
                    "yearly report",
                    "annual analysis",
                    "export everything",
                    "large dataset",
                    "big data",
                    "massive analysis",
                ],
                "data_indicators": [
                    "years?",
                    "months?",
                    "quarters?",
                    "all time",
                    "everything",
                    "entire",
                    "complete",
                    "full",
                ],
                "estimated_duration": 45,
            },
            # Complex operations (10-30 seconds)
            TaskComplexity.COMPLEX: {
                "keywords": [
                    "analyze",
                    "analysis",
                    "report",
                    "summarize",
                    "research",
                    "investigate",
                    "deep dive",
                    "study",
                    "calculate",
                    "process data",
                    "generate report",
                    "trends analysis",
                    "statistical analysis",
                ],
                "data_indicators": [
                    "month",
                    "quarter",
                    "week",
                    "daily",
                    "detailed",
                    "complex",
                    "advanced",
                    "comprehensive",
                ],
                "estimated_duration": 20,
            },
            # Moderate operations (2-10 seconds)
            TaskComplexity.MODERATE: {
                "keywords": [
                    "search",
                    "find",
                    "lookup",
                    "get",
                    "show",
                    "list",
                    "count",
                    "check",
                    "verify",
                ],
                "data_indicators": [
                    "recent",
                    "latest",
                    "current",
                    "today",
                    "this week",
                ],
                "estimated_duration": 5,
            },
        }

        # Threshold for automatic background processing (seconds)
        self.background_threshold = 8

        # Keywords that explicitly indicate analysis/research requests
        self.task_type_patterns = {
            "analysis": [
                "analyze",
                "analysis",
                "analytical",
                "examine",
                "data",
                "statistics",
                "metrics",
                "trends",
                "performance",
                "insights",
                "patterns",
            ],
            "research": [
                "research",
                "investigate",
                "study",
                "explore",
                "find information",
                "look up",
                "discover",
                "learn about",
                "tell me about",
            ],
            "reporting": [
                "report",
                "summary",
                "overview",
                "breakdown",
                "dashboard",
                "export",
                "generate",
            ],
        }

    def analyze_request(self, user_message: str) -> RequestAnalysis:
        """
        Analyze a user request to determine if it should be a background task.

        Args:
            user_message: The user's input message

        Returns:
            RequestAnalysis: Analysis result with recommendations
        """
        message_lower = user_message.lower().strip()

        # Extract potential complexity indicators
        detected_keywords = self._extract_complexity_keywords(message_lower)
        task_type = self._detect_task_type(message_lower)

        # Determine complexity level
        complexity, estimated_duration = self._assess_complexity(
            message_lower, detected_keywords
        )

        # Calculate confidence based on keyword matches and message structure
        confidence = self._calculate_confidence(
            message_lower, detected_keywords, task_type
        )

        # Determine if background processing is recommended
        should_background = (
            estimated_duration >= self.background_threshold
            or complexity in [TaskComplexity.COMPLEX, TaskComplexity.HEAVY]
        )

        # Generate explanation
        reason = self._generate_reason(
            complexity, estimated_duration, detected_keywords, task_type
        )

        return RequestAnalysis(
            complexity=complexity,
            estimated_duration_seconds=estimated_duration,
            should_background=should_background,
            detected_keywords=detected_keywords,
            task_type=task_type,
            confidence=confidence,
            reason=reason,
        )

    def _extract_complexity_keywords(self, message: str) -> List[str]:
        """Extract keywords that indicate request complexity"""
        found_keywords = []

        for complexity_level, patterns in self.complexity_patterns.items():
            # Check direct keywords
            for keyword in patterns["keywords"]:
                if keyword in message:
                    found_keywords.append(keyword)

            # Check data indicators
            for indicator in patterns["data_indicators"]:
                if indicator in message:
                    found_keywords.append(indicator)

        return list(set(found_keywords))  # Remove duplicates

    def _detect_task_type(self, message: str) -> Optional[str]:
        """Detect the type of task being requested"""
        task_scores = {}

        for task_type, keywords in self.task_type_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in message:
                    # Weight longer keywords more heavily
                    score += len(keyword.split())

            if score > 0:
                task_scores[task_type] = score

        # Return the task type with highest score
        if task_scores:
            return max(task_scores, key=task_scores.get)

        return None

    def _assess_complexity(
        self, message: str, keywords: List[str]
    ) -> Tuple[TaskComplexity, int]:
        """Assess the complexity level and estimated duration"""

        # Start with simple as default
        max_complexity = TaskComplexity.SIMPLE
        max_duration = 2

        # Check against complexity patterns
        for complexity_level, patterns in self.complexity_patterns.items():
            matches = 0

            # Count keyword matches
            for keyword in patterns["keywords"]:
                if keyword in message:
                    matches += 1

            # Count data indicator matches
            for indicator in patterns["data_indicators"]:
                if indicator in message:
                    matches += 1

            # If we have matches, consider this complexity level
            if matches > 0:
                if complexity_level.value == "heavy":
                    max_complexity = TaskComplexity.HEAVY
                    max_duration = patterns["estimated_duration"]
                    break  # Heavy is the highest, stop here
                elif (
                    complexity_level.value == "complex"
                    and max_complexity != TaskComplexity.HEAVY
                ):
                    max_complexity = TaskComplexity.COMPLEX
                    max_duration = patterns["estimated_duration"]
                elif (
                    complexity_level.value == "moderate"
                    and max_complexity == TaskComplexity.SIMPLE
                ):
                    max_complexity = TaskComplexity.MODERATE
                    max_duration = patterns["estimated_duration"]

        # Additional heuristics based on message characteristics
        word_count = len(message.split())

        # Long, detailed requests are often complex
        if word_count > 20:
            if max_complexity == TaskComplexity.SIMPLE:
                max_complexity = TaskComplexity.MODERATE
                max_duration = 5

        # Multiple question marks or specific technical terms
        if message.count("?") > 1 or any(
            term in message for term in ["algorithm", "optimization", "correlation"]
        ):
            if max_complexity in [TaskComplexity.SIMPLE, TaskComplexity.MODERATE]:
                max_complexity = TaskComplexity.COMPLEX
                max_duration = 15

        return max_complexity, max_duration

    def _calculate_confidence(
        self, message: str, keywords: List[str], task_type: Optional[str]
    ) -> float:
        """Calculate confidence in the complexity assessment"""
        confidence = 0.0

        # Base confidence from keyword matches
        if keywords:
            confidence += min(len(keywords) * 0.2, 0.6)

        # Boost confidence if task type is detected
        if task_type:
            confidence += 0.3

        # Message structure indicators
        if any(
            indicator in message
            for indicator in ["please", "can you", "i need", "help me"]
        ):
            confidence += 0.1

        # Technical specificity
        technical_terms = [
            "data",
            "analysis",
            "report",
            "system",
            "database",
            "performance",
        ]
        tech_matches = sum(1 for term in technical_terms if term in message)
        confidence += min(tech_matches * 0.05, 0.2)

        return min(confidence, 1.0)

    def _generate_reason(
        self,
        complexity: TaskComplexity,
        duration: int,
        keywords: List[str],
        task_type: Optional[str],
    ) -> str:
        """Generate human-readable explanation for the analysis"""

        reasons = []

        if complexity == TaskComplexity.HEAVY:
            reasons.append("Request appears to involve heavy data processing")
        elif complexity == TaskComplexity.COMPLEX:
            reasons.append("Request requires complex analysis or computation")
        elif complexity == TaskComplexity.MODERATE:
            reasons.append("Request involves moderate data processing")

        if duration >= 30:
            reasons.append(f"Estimated processing time: {duration}+ seconds")
        elif duration >= 10:
            reasons.append(f"Estimated processing time: {duration} seconds")

        if keywords:
            key_terms = ", ".join(keywords[:3])
            reasons.append(f"Detected complexity indicators: {key_terms}")

        if task_type:
            reasons.append(f"Identified as {task_type} task")

        return " | ".join(reasons) if reasons else "Basic complexity assessment"

    def should_use_background_processing(self, analysis: RequestAnalysis) -> bool:
        """
        Determine if request should automatically use background processing.

        Args:
            analysis: The request analysis result

        Returns:
            bool: True if background processing is recommended
        """
        return (
            analysis.should_background
            and analysis.confidence >= 0.4
            and analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.HEAVY]
        )
