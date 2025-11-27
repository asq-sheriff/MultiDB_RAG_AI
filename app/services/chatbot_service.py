"""Enhanced ChatbotService with Real LLM Integration & Advanced RAG"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable

# Import enhanced services
from app.services.knowledge_service import KnowledgeService

# Import generation service
try:
    from app.services.generation_service import GenerationService

    GENERATION_SERVICE_AVAILABLE = True
except ImportError:
    GenerationService = None
    GENERATION_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Type definitions
TelemetryFn = Callable[[str, Dict[str, Any]], None]


@dataclass
class ChatResponse:
    """Enhanced response structure for chatbot interactions"""

    message: str
    has_context: bool = False
    session_info: Dict[str, Any] = None
    timeout_transferred: bool = False
    background_task_id: str = None
    elapsed_time: float = None

    # Enhanced fields for real AI integration
    generation_used: bool = False
    context_sources: List[Dict[str, Any]] = None
    search_quality: Dict[str, Any] = None
    response_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.session_info is None:
            self.session_info = {}
        if self.context_sources is None:
            self.context_sources = []
        if self.search_quality is None:
            self.search_quality = {}
        if self.response_metadata is None:
            self.response_metadata = {}


def dict_to_chat_response(response_dict: Dict[str, Any]) -> ChatResponse:
    """Convert dictionary response to ChatResponse object for backward compatibility"""
    retrieval = response_dict.get("retrieval", {})

    return ChatResponse(
        message=response_dict.get("answer", response_dict.get("message", "")),
        has_context=bool(retrieval.get("results")),
        session_info=retrieval,
        timeout_transferred=response_dict.get("timeout_transferred", False),
        background_task_id=response_dict.get("background_task_id"),
        elapsed_time=response_dict.get("elapsed_time"),
        generation_used=response_dict.get("generation_used", False),
        context_sources=retrieval.get("results", []),
        search_quality=response_dict.get("search_quality", {}),
        response_metadata=response_dict.get("response_metadata", {}),
    )


@dataclass
class EnhancedChatbotConfig:
    """Enhanced chatbot configuration with real LLM integration"""

    # Search configuration
    route_default: str = os.getenv("ROUTER_DEFAULT_MODE", "auto")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "10"))
    max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "8000"))
    max_snippets: int = int(os.getenv("RAG_MAX_SNIPPETS", "5"))

    # RAG behavior
    include_kb: bool = os.getenv("RAG_INCLUDE_KB", "1") == "1"
    include_docs: bool = os.getenv("RAG_INCLUDE_DOCS", "1") == "1"
    rag_enabled: bool = os.getenv("RAG_ENABLED", "1") == "1"

    # Generation configuration - reads from your .env
    use_real_generation: bool = os.getenv("USE_REAL_GENERATION", "1") == "1"
    generation_max_tokens: int = int(
        os.getenv(
            "CHATBOT_GENERATION_MAX_TOKENS", os.getenv("GENERATION_MAX_TOKENS", "512")
        )
    )
    generation_temperature: float = float(
        os.getenv(
            "CHATBOT_GENERATION_TEMPERATURE", os.getenv("GENERATION_TEMPERATURE", "0.7")
        )
    )
    generation_timeout: float = float(
        os.getenv("CHATBOT_GENERATION_TIMEOUT", os.getenv("GENERATION_TIMEOUT", "30.0"))
    )

    # Response strategies
    response_strategy: str = os.getenv("RESPONSE_STRATEGY", "rag_enhanced")
    fallback_to_template: bool = os.getenv("FALLBACK_TO_TEMPLATE", "1") == "1"

    # Context optimization - reads from your .env
    context_window_optimization: bool = (
        os.getenv("CONTEXT_WINDOW_OPTIMIZATION", "1") == "1"
    )
    dynamic_context_adjustment: bool = (
        os.getenv("DYNAMIC_CONTEXT_ADJUSTMENT", "1") == "1"
    )

    # Advanced features
    enable_conversation_memory: bool = (
        os.getenv("ENABLE_CONVERSATION_MEMORY", "1") == "1"
    )
    max_conversation_history: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "5"))
    enable_streaming: bool = os.getenv("ENABLE_STREAMING", "0").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


# Backward compatibility
ChatbotConfig = EnhancedChatbotConfig


class EnhancedChatbotService:
    """Enhanced ChatbotService with real LLM integration and advanced RAG capabilities."""

    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        config: Optional[EnhancedChatbotConfig] = None,
        telemetry_cb: Optional[TelemetryFn] = None,
        generation_service: Optional[GenerationService] = None,
    ) -> None:
        """
        Initialize Enhanced ChatbotService.

        Args:
            knowledge_service: Enhanced KnowledgeService instance
            config: Enhanced configuration
            telemetry_cb: Optional telemetry callback
            generation_service: Optional GenerationService for real LLM responses
        """
        self.cfg = config or EnhancedChatbotConfig()
        self.ks = knowledge_service
        self._telemetry = telemetry_cb or (lambda kind, fields: None)
        self.generation_service = generation_service

        # Check if real generation is available and configured
        self.real_generation_available = (
            self.generation_service is not None
            and self.cfg.use_real_generation
            and GENERATION_SERVICE_AVAILABLE
        )

        logger.info("Enhanced ChatbotService initialized")
        logger.info(f"  Real generation available: {self.real_generation_available}")
        logger.info(f"  Response strategy: {self.cfg.response_strategy}")
        logger.info(f"  Context optimization: {self.cfg.context_window_optimization}")
        logger.info(f"  Max context chars: {self.cfg.max_context_chars}")

    async def answer_user_message(
        self,
        user_id: str,
        message: str,
        route: Optional[str] = None,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        response_strategy: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced message processing with real LLM generation and advanced RAG.

        Returns:
            {
                "answer": "...",
                "route": "auto->exact|hybrid|semantic",
                "retrieval": {...},
                "generation_used": bool,
                "search_quality": {...},
                "response_metadata": {...},
                "elapsed_time": float
            }
        """
        start_time = time.time()

        self._telemetry(
            "enhanced_chat_begin",
            {
                "user_id": user_id,
                "message_length": len(message),
                "real_generation_available": self.real_generation_available,
                "response_strategy": response_strategy or self.cfg.response_strategy,
            },
        )

        try:
            # 1. Store user message with enhanced metadata
            await self._persist_user_message(user_id, message, metadata or {})

            # 2. Enhanced RAG retrieval with Atlas Vector Search
            retrieval_payload = await self._execute_enhanced_rag(
                message, route, top_k, filters
            )

            context_text = self._build_enhanced_context_from_retrieval(
                retrieval_payload
            )
            search_quality = retrieval_payload.get("search_quality", {})

            # 3. Enhanced response generation with real LLM
            generation_strategy = response_strategy or self.cfg.response_strategy
            (
                answer,
                generation_used,
                response_metadata,
            ) = await self._generate_enhanced_response(
                user_id,
                message,
                context_text,
                generation_strategy,
                conversation_history,
            )

            # 4. Store assistant reply with enhanced metadata
            await self._persist_assistant_message(
                user_id,
                answer,
                {
                    "route": retrieval_payload.get("route"),
                    "generation_used": generation_used,
                    "search_quality": search_quality,
                    "response_metadata": response_metadata,
                    "context_length": len(context_text),
                    "elapsed_time": time.time() - start_time,
                },
            )

            elapsed_time = time.time() - start_time

            self._telemetry(
                "enhanced_chat_complete",
                {
                    "user_id": user_id,
                    "generation_used": generation_used,
                    "context_length": len(context_text),
                    "response_strategy": response_metadata.get("strategy", "unknown"),
                    "search_quality": search_quality.get(
                        "quality_assessment", "unknown"
                    ),
                    "elapsed_time": elapsed_time,
                },
            )

            return {
                "answer": answer,
                "route": retrieval_payload.get(
                    "route", route or self.cfg.route_default
                ),
                "retrieval": retrieval_payload,
                "generation_used": generation_used,
                "search_quality": search_quality,
                "response_metadata": response_metadata,
                "elapsed_time": elapsed_time,
            }

        except Exception as e:
            logger.exception(f"Enhanced chat processing failed: {e}")
            self._telemetry("enhanced_chat_error", {"error": str(e)})

            # Enhanced fallback response
            fallback_answer = self._enhanced_fallback_answer(message)
            elapsed_time = time.time() - start_time

            return {
                "answer": fallback_answer,
                "route": "error_fallback",
                "retrieval": {"results": [], "meta": {"error": str(e)}},
                "generation_used": False,
                "search_quality": {"quality_assessment": "error"},
                "response_metadata": {"strategy": "error_fallback", "error": str(e)},
                "elapsed_time": elapsed_time,
            }

    async def _execute_enhanced_rag(
        self,
        message: str,
        route: Optional[str],
        top_k: Optional[int],
        filters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute enhanced RAG retrieval with Atlas Vector Search"""

        route_eff = route or self.cfg.route_default
        top_k_eff = top_k or self.cfg.rag_top_k

        try:
            search_result = await self.ks.search_router(
                query=message,
                top_k=top_k_eff,
                route=route_eff,
                filters=filters,
                search_kb=self.cfg.include_kb,
                search_docs=self.cfg.include_docs,
            )

            self._telemetry(
                "enhanced_rag_success",
                {
                    "route": search_result.get("route"),
                    "results_count": len(search_result.get("results", [])),
                    "atlas_used": search_result.get("meta", {}).get(
                        "atlas_used", False
                    ),
                    "fallback_applied": search_result.get("fallback_applied", False),
                },
            )

            return search_result

        except Exception as e:
            logger.exception(f"Enhanced RAG retrieval failed: {e}")
            self._telemetry("enhanced_rag_error", {"error": str(e)})

            return {
                "query": message,
                "results": [],
                "route": "error",
                "meta": {"error": str(e)},
                "search_quality": {"quality_assessment": "error"},
            }

    def _build_enhanced_context_from_retrieval(
        self, retrieval_payload: Dict[str, Any]
    ) -> str:
        """Build OPTIMIZED context for faster generation"""

        snippets = retrieval_payload.get("results", [])
        if not snippets:
            return ""

        # AGGRESSIVE LIMITS for speed
        max_chars = 500  # Reduced from 8000!
        max_snippets = 2  # Reduced from 5!

        # Take only the best snippets
        ordered_snippets = sorted(
            snippets, key=lambda s: float(s.get("score", 0.0)), reverse=True
        )[:max_snippets]

        context_parts = []
        total_chars = 0

        for snippet in ordered_snippets:
            # Extract only the most relevant part
            content = snippet.get("content", snippet.get("answer", ""))[:200]

            if total_chars + len(content) > max_chars:
                break

            context_parts.append(content)
            total_chars += len(content)

        if not context_parts:
            return ""

        # Simple, short context
        return "Context: " + " ".join(context_parts)

    def _format_faq_for_llm(self, snippet: Dict[str, Any], index: int) -> str:
        """Format FAQ snippet optimized for LLM consumption"""
        question = snippet.get("question", "").strip()
        answer = snippet.get("answer", "").strip()
        score = snippet.get("score", 0.0)
        source = snippet.get("source", "")

        if not question or not answer:
            return ""

        return f"## {index}. FAQ: {question}\n\n**Answer:** {answer}\n\n*Source: {source} (relevance: {score:.2f})*"

    def _format_document_for_llm(self, snippet: Dict[str, Any], index: int) -> str:
        """Format document snippet optimized for LLM consumption"""
        title = snippet.get("title", "Document").strip()
        content = snippet.get("content", "").strip()
        score = snippet.get("score", 0.0)
        source = snippet.get("source", "")

        if not content:
            return ""

        return f"## {index}. Document: {title}\n\n{content}\n\n*Source: {source} (relevance: {score:.2f})*"

    def _get_dynamic_context_limit(self, query_length: int) -> int:
        """Dynamically adjust context limit based on generation service capabilities"""
        base_limit = self.cfg.max_context_chars

        if not self.cfg.dynamic_context_adjustment:
            return base_limit

        # Adjust based on generation service context window
        if self.real_generation_available and hasattr(
            self.generation_service, "config"
        ):
            generation_config = self.generation_service.config
            available_context = getattr(generation_config, "max_context_length", 8192)

            # Reserve space for system prompt, user query, and generation
            reserved_space = query_length + 1500  # Buffer for prompts and generation
            dynamic_limit = max(available_context - reserved_space, base_limit // 2)

            return min(dynamic_limit, base_limit)

        return base_limit

    async def _generate_enhanced_response(
        self,
        user_id: str,
        message: str,
        context: str,
        strategy: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """Generate enhanced response using real LLM with advanced strategies"""

        generation_used = False
        response_metadata = {"strategy": strategy}

        try:
            if strategy == "generation_only" and self.real_generation_available:
                # Pure LLM generation without RAG context
                answer = await self._generate_llm_response(
                    user_id, message, "", conversation_history
                )
                generation_used = True
                response_metadata.update(
                    {"strategy": "generation_only", "context_used": False}
                )

            elif strategy == "rag_enhanced" and self.real_generation_available:
                # Enhanced RAG with real LLM (preferred)
                answer = await self._generate_rag_enhanced_response(
                    user_id, message, context, conversation_history
                )
                generation_used = True
                response_metadata.update(
                    {
                        "strategy": "rag_enhanced",
                        "context_used": bool(context),
                        "context_length": len(context),
                    }
                )

            elif strategy == "template_only":
                # Template-based response only
                answer = self._generate_template_response(message, context)
                response_metadata["strategy"] = "template_only"

            else:
                # Intelligent fallback strategy
                if self.real_generation_available and self.cfg.fallback_to_template:
                    try:
                        # Try real LLM first
                        answer = await self._generate_rag_enhanced_response(
                            user_id, message, context, conversation_history
                        )
                        generation_used = True
                        response_metadata.update(
                            {
                                "strategy": "rag_enhanced_fallback",
                                "context_used": bool(context),
                            }
                        )
                    except Exception as gen_error:
                        logger.warning(
                            f"LLM generation failed, using template: {gen_error}"
                        )
                        answer = self._generate_template_response(message, context)
                        response_metadata.update(
                            {
                                "strategy": "template_fallback",
                                "generation_error": str(gen_error),
                            }
                        )
                else:
                    # Template-only fallback
                    answer = self._generate_template_response(message, context)
                    response_metadata["strategy"] = "template_fallback"

            return answer, generation_used, response_metadata

        except Exception as e:
            logger.exception(f"Enhanced response generation failed: {e}")

            # Final fallback
            answer = self._enhanced_fallback_answer(message, context)
            response_metadata.update({"strategy": "error_fallback", "error": str(e)})

            return answer, False, response_metadata

    async def _generate_rag_enhanced_response(
        self,
        user_id: str,
        message: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate RAG-enhanced response with SMART token limits"""

        if not self.real_generation_available:
            raise RuntimeError("Real generation service not available")

        # SMART TOKEN LIMITS based on query type
        # Short answers for simple questions
        if any(
            word in message.lower()
            for word in ["what is", "define", "explain briefly", "who is"]
        ):
            max_tokens = 100  # Short response
        elif "?" in message and len(message) < 50:
            max_tokens = 75  # Simple question
        else:
            max_tokens = 150  # Standard response (not 256!)

        messages = self._build_enhanced_chat_messages(
            user_id, message, context, conversation_history
        )

        try:
            response = await self.generation_service.chat_completion(
                messages=messages,
                max_tokens=max_tokens,  # Use smart limit
                temperature=self.cfg.generation_temperature,
                stream=False,
            )

            # Handle async generator if needed
            if hasattr(response, "__aiter__"):
                chunks = []
                async for chunk in response:
                    chunks.append(str(chunk))
                response = "".join(chunks)

            return self._post_process_llm_response(response)

        except Exception as e:
            logger.error(f"RAG-enhanced generation failed: {e}")
            raise

    async def _generate_llm_response(
        self,
        user_id: str,
        message: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate response using real LLM (with or without context)"""

        if not self.real_generation_available:
            raise RuntimeError("Real generation service not available")

        # Build prompt for direct generation
        prompt_parts = []

        if conversation_history and self.cfg.enable_conversation_memory:
            prompt_parts.append("Previous conversation:")
            for msg in conversation_history[-self.cfg.max_conversation_history :]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.title()}: {content}")
            prompt_parts.append("")

        if context:
            prompt_parts.append(f"Context:\n{context}\n")

        prompt_parts.append(f"User: {message}\n\nAssistant:")
        prompt = "\n".join(prompt_parts)

        try:
            response = await self.generation_service.generate(
                prompt=prompt,
                max_tokens=self.cfg.generation_max_tokens,
                temperature=self.cfg.generation_temperature,
                stream=False,  # CHANGED: Force non-streaming
            )

            # ADDED: Handle async generator if returned
            if hasattr(response, "__aiter__"):
                chunks = []
                async for chunk in response:
                    chunks.append(str(chunk))
                response = "".join(chunks)

            return self._post_process_llm_response(response)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _build_enhanced_chat_messages(
        self,
        user_id: str,
        message: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """Build OPTIMIZED chat messages for speed"""

        messages = []

        # Shorter system message
        system_prompt = "You are a helpful AI assistant."

        if context and len(context) < 300:  # Only include short context
            system_prompt += f"\n{context}"

        messages.append({"role": "system", "content": system_prompt})

        # Skip conversation history for speed
        # Just add the current message
        messages.append({"role": "user", "content": message})

        return messages

    def _post_process_llm_response(self, response: Any) -> str:
        """Post-process LLM response for consistency and quality"""

        # ADDED: Type checking and conversion
        if response is None:
            return "I apologize, but I couldn't generate a proper response. Please try again."

        # Handle different response types
        if not isinstance(response, str):
            # Try to convert to string
            try:
                response = str(response)
            except Exception:
                return (
                    "I apologize, but I encountered an issue processing the response."
                )

        if not response:
            return "I apologize, but I couldn't generate a proper response. Please try again."

        # Clean up response
        response = response.strip()

        # Remove potential artifacts
        if response.startswith("Assistant:"):
            response = response[10:].strip()
        if response.startswith("Answer:"):
            response = response[7:].strip()

        # Ensure reasonable length
        max_length = self.cfg.generation_max_tokens * 4  # Rough char estimate
        if len(response) > max_length:
            response = response[:max_length] + "..."

        # Ensure minimum quality
        if len(response) < 10:
            return "I need more information to provide a helpful response. Could you please elaborate on your question?"

        return response

    def _generate_template_response(self, message: str, context: str) -> str:
        """Enhanced template-based response generation"""

        if context:
            # Extract key information from context for template
            context_preview = context[:800] + "..." if len(context) > 800 else context

            return (
                "Based on the available information:\n\n"
                f"{context_preview}\n\n"
                f'This should help address your question about: "{message[:100]}..."\n\n'
                "If you need more specific details, please let me know!"
            )
        else:
            return (
                f'I understand you\'re asking about: "{message[:100]}..."\n\n'
                "I don't have specific information available right now, but I'd be happy to help "
                "if you could provide more details or rephrase your question."
            )

    def _enhanced_fallback_answer(self, message: str, context: str = "") -> str:
        """Enhanced fallback response with better user experience"""

        if context:
            return (
                "I found some related information but encountered an issue generating a complete response. "
                "The system is experiencing temporary difficulties. Please try rephrasing your question or try again in a moment."
            )
        else:
            return (
                "I'm experiencing temporary difficulties processing your request. "
                "Please try again in a moment or rephrase your question. "
                "If the issue persists, please contact support."
            )

    async def _persist_user_message(
        self, user_id: str, message: str, metadata: Dict[str, Any]
    ) -> None:
        """Enhanced user message persistence with metadata"""
        try:
            _enhanced_metadata = {
                **metadata,
                "real_generation_available": self.real_generation_available,
                "rag_enabled": self.cfg.rag_enabled,
                "timestamp": time.time(),
                "service_version": "enhanced_v2",
            }

            # Integration point for conversation history storage
            # This would integrate with ScyllaDB enhanced conversation history

        except Exception as e:
            logger.warning(f"Enhanced user message persistence failed: {e}")

    async def _persist_assistant_message(
        self, user_id: str, message: str, metadata: Dict[str, Any]
    ) -> None:
        """Enhanced assistant message persistence with generation metadata"""
        try:
            _enhanced_metadata = {
                **metadata,
                "message_length": len(message),
                "real_ai_used": metadata.get("generation_used", False),
                "timestamp": time.time(),
                "service_version": "enhanced_v2",
            }

            # Integration point for conversation history storage
            # This would integrate with ScyllaDB enhanced conversation history

        except Exception as e:
            logger.warning(f"Enhanced assistant message persistence failed: {e}")


# Backward compatibility
ChatbotService = EnhancedChatbotService
