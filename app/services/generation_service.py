"""Qwen3-1.7B Generation Service Optimized for Apple Silicon (MPS)"""

from __future__ import annotations

import asyncio
import gc
import logging
import os
import time
import threading
import torch
from typing import List, Optional, Dict, Any, Union, AsyncIterator
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    GenerationConfig as HFGenerationConfig,
)

logger = logging.getLogger(__name__)

# Force MPS optimizations
if torch.backends.mps.is_available():
    torch.set_float32_matmul_precision("medium")  # Faster matmul on MPS


@dataclass
class GenerationConfig:
    """Qwen3-1.7B configuration optimized for Apple Silicon MPS"""

    # Model - keeping Qwen for quality
    model_name: str = os.getenv("GENERATION_MODEL_NAME", "Qwen/Qwen3-1.7B")

    # MPS Optimizations
    device: str = "mps"  # Force MPS
    torch_dtype: str = "float16"  # Critical for MPS performance
    use_fast_tokenizer: bool = True  # Faster tokenization

    # Memory optimizations
    low_cpu_mem_usage: bool = True
    offload_folder: str = "/tmp/offload"  # Offload some layers if needed
    max_memory: Dict[str, str] = None  # Will set dynamically

    # Generation parameters (optimized for speed)
    fast_mode: bool = os.getenv("GENERATION_FAST_MODE", "true").lower() == "true"
    max_input_tokens: int = int(os.getenv("GENERATION_MAX_INPUT_TOKENS", "256"))
    max_output_tokens: int = int(os.getenv("GENERATION_MAX_OUTPUT_TOKENS", "100"))
    max_new_tokens: int = int(os.getenv("GENERATION_MAX_TOKENS", "100"))
    min_new_tokens: int = 10  # Prevent too-short responses
    temperature: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("GENERATION_TOP_P", "0.9"))
    top_k: int = int(os.getenv("GENERATION_TOP_K", "40"))
    repetition_penalty: float = float(os.getenv("GENERATION_REPETITION_PENALTY", "1.1"))
    do_sample: bool = True

    # MPS-specific optimizations
    use_cache: bool = True  # KV cache for faster generation
    num_beams: int = 1  # Beam search is slow on MPS, use greedy
    early_stopping: bool = True

    # Performance settings
    batch_size: int = 1  # MPS works best with batch_size=1
    max_length: int = 512 if fast_mode else 2048  # Reduce from 8192 for speed
    truncation: bool = True
    padding: str = "left"  # Left padding for generation

    # Threading
    thread_pool_workers: int = 1
    generation_timeout_seconds: float = float(os.getenv("GENERATION_TIMEOUT", "30.0"))

    # Preprocessing
    remove_invalid_values: bool = True  # Clean inputs

    enable_postgresql: bool = (
        os.getenv("GENERATION_ENABLE_POSTGRESQL", "false").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "GenerationConfig":
        """Create MPS-optimized config"""
        config = cls()

        # Set max memory for MPS
        if torch.backends.mps.is_available():
            # Allocate most memory to MPS, leave some for system
            config.max_memory = {"mps": "10GB", "cpu": "4GB"}

        return config


class GenerationService:
    """Qwen3-1.7B service optimized for Apple Silicon MPS"""

    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig.from_env()

        # Model components
        self._tokenizer = None
        self._model = None
        self._generation_config = None
        self._device = None

        # Optimization flags
        self._model_compiled = False
        self._using_mps = torch.backends.mps.is_available()

        # Threading
        self._model_lock = threading.Lock()
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self.config.thread_pool_workers
        )

        # Performance tracking
        self._load_time = None
        self._first_generation = True
        self._generation_count = 0
        self._total_generation_time = 0.0

        logger.info(
            f"Qwen3-1.7B Service initialized (MPS available: {self._using_mps})"
        )

    @property
    def is_ready(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None

    async def ensure_model_loaded(self):
        """Ensure model is loaded with MPS optimizations"""
        if not self.is_ready:
            logger.info("Loading Qwen3-1.7B with MPS optimizations...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._thread_pool, self._load_model_optimized)

    def _load_model_optimized(self):
        """Load Qwen3-1.7B with Apple Silicon optimizations"""
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            start_time = time.time()
            logger.info("Loading Qwen3-1.7B with MPS optimizations...")

            try:
                # 1. Load tokenizer with optimizations
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_name,
                    use_fast=self.config.use_fast_tokenizer,
                    trust_remote_code=True,
                    padding_side=self.config.padding,
                    truncation_side="left",
                )

                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token

                # 2. Determine optimal dtype for MPS
                if self._using_mps:
                    dtype = torch.float16  # Critical for MPS speed
                    device_map = None  # Don't use auto device map with MPS
                else:
                    dtype = torch.float32
                    device_map = "auto"

                logger.info(f"Using dtype: {dtype}, device: mps")

                # 3. Load model with MPS optimizations
                model_kwargs = {
                    "torch_dtype": dtype,
                    "trust_remote_code": True,
                    "low_cpu_mem_usage": self.config.low_cpu_mem_usage,
                }

                # Don't use device_map with MPS
                if not self._using_mps:
                    model_kwargs["device_map"] = device_map

                self._model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_name, **model_kwargs
                )

                # 4. Move model to MPS and optimize
                if self._using_mps:
                    logger.info("Moving model to MPS...")
                    self._model = self._model.to("mps")
                    self._device = torch.device("mps")

                    # Enable MPS optimizations
                    self._model.eval()  # Set to eval mode

                    """
                    # Try to compile model for MPS (experimental)
                    try:
                        if hasattr(torch, 'compile'):
                            logger.info("Attempting torch.compile for MPS...")
                            self._model = torch.compile(
                                self._model,
                                mode="reduce-overhead",
                                backend="aot_eager"  # MPS-compatible backend
                            )
                            self._model_compiled = True
                            logger.info("✅ Model compiled for MPS")
                    except Exception as e:
                        logger.debug(f"torch.compile not available or failed: {e}")
                    """
                    self._model_compiled = False  # Just set to False
                    logger.info("Skipping torch.compile for better stability")

                # 5. Create optimized generation config
                self._generation_config = HFGenerationConfig(
                    max_new_tokens=self.config.max_new_tokens,
                    min_new_tokens=self.config.min_new_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                    repetition_penalty=self.config.repetition_penalty,
                    do_sample=self.config.do_sample,
                    num_beams=self.config.num_beams,
                    early_stopping=self.config.early_stopping,
                    use_cache=self.config.use_cache,
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                )

                self._load_time = time.time() - start_time
                logger.info(f"✅ Qwen3-1.7B loaded in {self._load_time:.1f}s")

                # 6. Warmup
                self._warmup_model()

            except Exception as e:
                logger.error(f"Failed to load Qwen3-1.7B: {e}")
                raise RuntimeError(f"Model loading failed: {e}")

    def _warmup_model(self):
        """Warmup model to pre-compile kernels"""
        try:
            logger.info("Warming up Qwen3-1.7B...")

            with torch.inference_mode():
                inputs = self._tokenizer(
                    "Hello", return_tensors="pt", truncation=True, max_length=10
                ).to(self._device)

                with torch.amp.autocast("mps", dtype=torch.float16):
                    _ = self._model.generate(
                        **inputs, max_new_tokens=5, do_sample=False, use_cache=True
                    )

            logger.info("✅ Model warmed up")

        except Exception as e:
            logger.warning(f"Warmup failed (non-critical): {e}")

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate text with MPS optimizations"""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Ensure model is loaded
        await self.ensure_model_loaded()

        # Force non-streaming for stability
        # stream disabled for stability

        start_time = time.time()

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._thread_pool,
                    self._generate_optimized,
                    prompt,
                    max_tokens,
                    temperature,
                    kwargs,
                ),
                timeout=self.config.generation_timeout_seconds,
            )

            elapsed = time.time() - start_time
            self._generation_count += 1
            self._total_generation_time += elapsed

            # Log performance
            if self._first_generation:
                logger.info(f"First generation (includes compilation): {elapsed:.2f}s")
                self._first_generation = False
            elif elapsed > 15:
                logger.warning(f"Slow generation: {elapsed:.2f}s")
            else:
                logger.debug(f"Generation: {elapsed:.2f}s")

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"Generation timeout after {self.config.generation_timeout_seconds}s"
            )
            return "Generation timed out. Please try with a shorter prompt."
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "Generation failed. Please try again."

    def _generate_optimized(
        self,
        prompt: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        extra_kwargs: Dict[str, Any],
    ) -> str:
        """MPS-optimized generation with aggressive truncation and speed optimizations"""

        try:
            # CRITICAL: Limit input length for speed
            max_input_tokens = 256 if self.config.fast_mode else 512

            # CAP output tokens for speed (more aggressive)
            if max_tokens:
                max_tokens = min(max_tokens, 100 if self.config.fast_mode else 150)
            else:
                max_tokens = 75 if self.config.fast_mode else 100

            # Intelligent truncation for long prompts
            if len(prompt) > 1000:
                # Keep system message and last part of conversation
                if "System:" in prompt and "User:" in prompt:
                    parts = prompt.split("\n\n")
                    system_parts = [p for p in parts if p.startswith("System:")]
                    user_parts = [p for p in parts if p.startswith("User:")]

                    if system_parts and user_parts:
                        # Take only the FIRST 100 chars of system and LAST user message
                        system_msg = system_parts[0][:200] if system_parts[0] else ""
                        user_msg = user_parts[-1]
                        prompt = f"{system_msg}\n\n{user_msg}\n\nAssistant:"
                        logger.debug(
                            f"Intelligently truncated prompt to {len(prompt)} chars"
                        )

            # Tokenize with strict truncation
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=max_input_tokens,
                padding=False,
                return_attention_mask=True,  # Explicitly request attention mask
            )

            # Log if truncation happened
            if self.config.fast_mode:  # Only log in non-fast mode to reduce overhead
                original_tokens = len(self._tokenizer.encode(prompt))
                if original_tokens > max_input_tokens:
                    logger.debug(
                        f"Input truncated: {original_tokens} -> {max_input_tokens} tokens"
                    )

            # Move to device
            if self._using_mps:
                inputs = {k: v.to("mps") for k, v in inputs.items()}

            # Create a COPY of generation config (don't modify shared config!)
            from transformers import GenerationConfig as HFGenerationConfig

            gen_config = HFGenerationConfig(
                max_new_tokens=max_tokens,
                min_new_tokens=10,  # Prevent too-short responses
                temperature=temperature or (0.5 if self.config.fast_mode else 0.7),
                top_p=0.9,
                top_k=40 if not self.config.fast_mode else 20,  # Smaller k for speed
                repetition_penalty=1.1,
                do_sample=not self.config.fast_mode,  # Greedy for fast mode!
                num_beams=1,  # No beam search for speed
                early_stopping=True,
                use_cache=True,  # KV cache for speed
                pad_token_id=self._tokenizer.pad_token_id,
                eos_token_id=self._tokenizer.eos_token_id,
                return_dict_in_generate=False,  # Slightly faster
                output_scores=False,  # Don't need scores
                output_attentions=False,  # Don't need attentions
                output_hidden_states=False,  # Don't need hidden states
            )

            # Remove unwanted parameters from extra_kwargs
            # These can slow down generation
            extra_kwargs.pop("output_scores", None)
            extra_kwargs.pop("output_attentions", None)
            extra_kwargs.pop("output_hidden_states", None)
            extra_kwargs.pop("return_dict_in_generate", None)

            # Generate with optimizations
            with torch.inference_mode():  # Faster than no_grad
                if self._using_mps:
                    # Use autocast for MPS
                    with torch.amp.autocast("mps", dtype=torch.float16):
                        outputs = self._model.generate(
                            input_ids=inputs["input_ids"],
                            attention_mask=inputs["attention_mask"],
                            generation_config=gen_config,
                            **extra_kwargs,
                        )

                        # Clear MPS cache after generation to prevent memory buildup
                        if self.config.fast_mode:
                            torch.mps.empty_cache()
                else:
                    outputs = self._model.generate(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        generation_config=gen_config,
                        **extra_kwargs,
                    )

            # Efficient decoding
            # Only decode the generated tokens (not the input)
            generated_ids = outputs[0][inputs["input_ids"].shape[-1] :]

            # Decode with minimal processing
            response = self._tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False if self.config.fast_mode else True,
            )

            # Quick cleanup and return
            response = response.strip()

            # Ensure minimum response length
            if len(response) < 10 and not self.config.fast_mode:
                logger.warning(f"Very short response generated: {len(response)} chars")

            return response

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                logger.error(
                    "MPS out of memory - clearing cache and retrying with smaller context"
                )
                torch.mps.empty_cache()
                # Retry with even smaller context
                if len(prompt) > 500:
                    return self._generate_optimized(
                        prompt[-500:],  # Take last 500 chars only
                        max_tokens=50,  # Smaller output
                        temperature=temperature,
                        extra_kwargs={},
                    )
                return "Memory error. Please try with a shorter prompt."
            else:
                logger.error(f"Generation runtime error: {e}")
                return "Generation failed. Please try again."

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "An error occurred during generation."

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[str, AsyncIterator[str]]:
        """Chat completion with Qwen formatting"""

        # Use Qwen's chat template if available
        if hasattr(self._tokenizer, "apply_chat_template"):
            try:
                prompt = self._tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                prompt = self._format_chat_messages(messages)
        else:
            prompt = self._format_chat_messages(messages)

        return await self.generate(prompt, max_tokens, temperature, stream, **kwargs)

    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Qwen"""
        formatted = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "").strip()

            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")

        formatted.append("Assistant:")
        return "\n\n".join(formatted)

    @property
    def performance_stats(self) -> Dict[str, Any]:
        """Performance statistics"""
        avg_time = self._total_generation_time / max(self._generation_count, 1)

        return {
            "model_name": self.config.model_name,
            "device": "mps" if self._using_mps else "cpu",
            "compiled": self._model_compiled,
            "model_load_time_seconds": self._load_time,
            "total_generations": self._generation_count,
            "average_generation_time_seconds": avg_time,
            "using_fp16": self._using_mps,
            "is_ready": self.is_ready,
        }

    async def warmup(self) -> Dict[str, Any]:
        """Warmup with performance test"""
        logger.info("Running Qwen3-1.7B warmup...")
        start_time = time.time()

        try:
            await self.ensure_model_loaded()

            # Test generation
            test_prompts = [
                "Hello, how are you?",
                "What is 2+2?",
            ]

            for prompt in test_prompts:
                response = await self.generate(prompt, max_tokens=20)
                logger.debug(f"Warmup response: {response[:50]}...")

            warmup_time = time.time() - start_time

            return {
                "warmup_successful": True,
                "warmup_time_seconds": warmup_time,
                **self.performance_stats,
            }

        except Exception as e:
            logger.error(f"Warmup failed: {e}")
            return {"warmup_successful": False, "error": str(e)}

    def cleanup_memory(self):
        """Clean up MPS memory"""
        if self._using_mps:
            try:
                torch.mps.empty_cache()
                torch.mps.synchronize()
            except Exception:
                pass
        gc.collect()

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, "_thread_pool"):
            self._thread_pool.shutdown(wait=False)

        self.cleanup_memory()

        if hasattr(self, "_model"):
            del self._model
        if hasattr(self, "_tokenizer"):
            del self._tokenizer


# Backward compatibility
EnhancedGenerationService = GenerationService
