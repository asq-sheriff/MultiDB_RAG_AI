import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import secrets

load_dotenv()


@dataclass
class EmbeddingConfig:
    model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
    )
    fallback_model: str = os.getenv(
        "EMBEDDING_FALLBACK_MODEL", "mlx-community/all-MiniLM-L6-v2-4bit"
    )
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
    max_sequence_length: int = int(os.getenv("EMBEDDING_MAX_LENGTH", "2048"))
    normalize_embeddings: bool = (
        os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
    )
    use_fp16: bool = os.getenv("EMBEDDING_USE_FP16", "true").lower() == "true"
    device: Optional[str] = os.getenv("EMBEDDING_DEVICE")
    enable_mps: bool = os.getenv("EMBEDDING_ENABLE_MPS", "true").lower() == "true"
    max_cache_size_mb: int = int(os.getenv("EMBEDDING_CACHE_MB", "2048"))
    thread_pool_workers: int = int(os.getenv("EMBEDDING_THREADS", "2"))
    memory_cleanup_threshold: float = float(
        os.getenv("MEMORY_CLEANUP_THRESHOLD", "0.75")
    )
    query_timeout_seconds: float = float(os.getenv("EMBEDDING_QUERY_TIMEOUT", "10.0"))
    batch_timeout_seconds: float = float(os.getenv("EMBEDDING_BATCH_TIMEOUT", "120.0"))
    enable_postgresql: bool = (
        os.getenv("EMBEDDING_ENABLE_POSTGRESQL", "false").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        return cls()


@dataclass
class GenerationConfig:
    model_name: str = os.getenv("GENERATION_MODEL_NAME", "Qwen/Qwen3-1.7B")
    target_model: str = "deepseek/deepseek-r1-0528-qwen3-8b"
    fallback_model: str = os.getenv(
        "GENERATION_FALLBACK_MODEL", "mlx-community/Mistral-7B-Instruct-v0.2-4-bit"
    )
    quantization: str = os.getenv("GENERATION_QUANTIZATION", "mlx")
    load_in_4bit: bool = os.getenv("GENERATION_4BIT", "false").lower() == "true"
    load_in_8bit: bool = os.getenv("GENERATION_8BIT", "false").lower() == "true"
    max_context_length: int = int(os.getenv("GENERATION_MAX_CONTEXT", "4096"))
    max_new_tokens: int = int(os.getenv("GENERATION_MAX_TOKENS", "1024"))
    context_window_adjustment: bool = (
        os.getenv("GENERATION_CONTEXT_ADJUSTMENT", "true").lower() == "true"
    )
    dynamic_context_scaling: bool = (
        os.getenv("DYNAMIC_CONTEXT_SCALING", "true").lower() == "true"
    )
    device: Optional[str] = os.getenv("GENERATION_DEVICE")
    enable_mps: bool = os.getenv("GENERATION_ENABLE_MPS", "true").lower() == "true"
    prefer_mlx: bool = os.getenv("GENERATION_PREFER_MLX", "true").lower() == "true"
    temperature: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("GENERATION_TOP_P", "0.9"))
    top_k: int = int(os.getenv("GENERATION_TOP_K", "40"))
    repetition_penalty: float = float(
        os.getenv("GENERATION_REPETITION_PENALTY", "1.05")
    )
    batch_size: int = int(os.getenv("GENERATION_BATCH_SIZE", "1"))
    thread_pool_workers: int = int(os.getenv("GENERATION_THREADS", "1"))
    memory_cleanup_threshold: float = float(
        os.getenv("MEMORY_CLEANUP_THRESHOLD", "0.80")
    )
    enable_streaming: bool = os.getenv("ENABLE_STREAMING", "false").lower() == "true"
    generation_timeout_seconds: float = float(os.getenv("GENERATION_TIMEOUT", "60.0"))
    enable_postgresql: bool = (
        os.getenv("GENERATION_ENABLE_POSTGRESQL", "false").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "GenerationConfig":
        return cls()


@dataclass
class AtlasVectorSearchConfig:
    atlas_uri: Optional[str] = os.getenv("MONGO_ATLAS_URI")
    cluster_name: str = os.getenv("ATLAS_CLUSTER_NAME", "chatbot-vector-search")
    vector_index_name: str = os.getenv("ATLAS_VECTOR_INDEX_NAME", "vector_index")
    embedding_field: str = "embedding"
    embedding_dimension: int = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
    similarity_metric: str = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")
    num_candidates_multiplier: int = int(os.getenv("ATLAS_CANDIDATES_MULTIPLIER", "10"))
    max_candidates: int = int(os.getenv("ATLAS_MAX_CANDIDATES", "1000"))
    enable_atlas_search: bool = os.getenv("ENABLE_ATLAS_SEARCH", "auto") != "false"
    enable_manual_fallback: bool = (
        os.getenv("ENABLE_MANUAL_FALLBACK", "true") != "false"
    )
    manual_fallback_threshold: int = int(
        os.getenv("MANUAL_FALLBACK_THRESHOLD", "10000")
    )


@dataclass
class SearchConfig:
    enable_exact_search_fallback: bool = (
        os.getenv("ENABLE_EXACT_SEARCH_FALLBACK", "true") == "true"
    )
    enable_semantic_search_fallback: bool = (
        os.getenv("ENABLE_SEMANTIC_SEARCH_FALLBACK", "true") == "true"
    )
    min_exact_results: int = int(os.getenv("MIN_EXACT_RESULTS", "1"))
    min_semantic_score: float = float(os.getenv("MIN_SEMANTIC_SCORE", "0.3"))
    candidate_multiplier_default: int = int(os.getenv("CANDIDATE_MULTIPLIER", "8"))
    candidate_multiplier_fallback: int = int(
        os.getenv("CANDIDATE_MULTIPLIER_FALLBACK", "12")
    )
    max_fallback_attempts: int = int(os.getenv("MAX_FALLBACK_ATTEMPTS", "2"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "10"))
    rag_max_snippets: int = int(os.getenv("RAG_MAX_SNIPPETS", "5"))
    rag_diversity_threshold: float = float(os.getenv("RAG_DIVERSITY_THRESHOLD", "0.85"))


@dataclass
class ScyllaConfig:
    hosts: list = None
    port: int = 9042
    keyspace: str = "chatbot_ks"
    datacenter: str = "datacenter1"
    connect_timeout: int = 15
    control_connection_timeout: int = 15
    protocol_version: int = 4
    max_retries: int = 3
    retry_delay: float = 2.0

    def __post_init__(self):
        if self.hosts is None:
            self.hosts = ["127.0.0.1"]

    @classmethod
    def get_scylla_config(cls) -> dict:
        instance = cls()
        return {
            "hosts": instance.hosts,
            "port": instance.port,
            "keyspace": instance.keyspace,
            "datacenter": instance.datacenter,
            "connect_timeout": instance.connect_timeout,
            "control_connection_timeout": instance.control_connection_timeout,
            "protocol_version": instance.protocol_version,
            "max_retries": instance.max_retries,
            "retry_delay": instance.retry_delay,
        }


@dataclass
class RedisConfig:
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    default_cache_ttl: int = 3600
    session_ttl: int = 86400
    analytics_ttl: int = 604800
    ai_cache_ttl: int = 1800


@dataclass
class PostgreSQLConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "chatbot_app")
    username: str = os.getenv("POSTGRES_USER", "chatbot_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "secure_password")
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class MongoConfig:
    host: str = os.getenv("MONGO_HOST", "localhost")
    port: int = int(os.getenv("MONGO_PORT", "27017"))
    username: str = os.getenv("MONGO_USER", "root")
    password: str = os.getenv("MONGO_PASSWORD", "example")
    database: str = os.getenv("MONGO_DB", "chatbot_app")
    max_pool_size: int = 20
    min_pool_size: int = 5
    server_selection_timeout_ms: int = 5000
    connect_timeout_ms: int = 5000
    socket_timeout_ms: int = 10000
    conversations_collection: str = "conversations"
    knowledge_base_collection: str = "knowledge_base"
    embeddings_collection: str = "embeddings"
    documents_collection: str = "documents"
    knowledge_vectors_collection: str = "knowledge_vectors"
    embedding_dimension: int = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
    synthetic_embedding_dimension: int = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))
    vector_index_name: str = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")
    similarity_metric: str = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")

    @property
    def db_name(self) -> str:
        return self.database

    @property
    def connection_uri(self) -> str:
        return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/"

    @property
    def atlas_uri(self) -> Optional[str]:
        return os.getenv("MONGO_ATLAS_URI")

    def build_uri(self) -> str:
        atlas_uri = self.atlas_uri
        if atlas_uri:
            return atlas_uri
        return self.connection_uri

    def get_connection_settings(self) -> dict:
        return {
            "serverSelectionTimeoutMS": self.server_selection_timeout_ms,
            "connectTimeoutMS": self.connect_timeout_ms,
            "socketTimeoutMS": self.socket_timeout_ms,
            "maxPoolSize": self.max_pool_size,
            "minPoolSize": self.min_pool_size,
        }


@dataclass
class ApplicationConfig:
    scylla: ScyllaConfig
    redis: RedisConfig
    postgresql: PostgreSQLConfig
    mongo: MongoConfig
    embedding: EmbeddingConfig
    generation: GenerationConfig
    atlas_search: AtlasVectorSearchConfig
    search: SearchConfig

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_rate_limit: int = int(os.getenv("API_RATE_LIMIT", "100"))
    max_chat_history: int = 50

    enable_caching: bool = True
    enable_analytics: bool = True
    enable_notifications: bool = True
    enable_postgresql: bool = os.getenv("ENABLE_POSTGRESQL", "true").lower() == "true"
    enable_mongodb: bool = os.getenv("ENABLE_MONGODB", "true").lower() == "true"

    use_real_embeddings: bool = os.getenv("USE_REAL_EMBEDDINGS", "1") == "1"
    use_real_generation: bool = os.getenv("USE_REAL_GENERATION", "1") == "1"
    use_synthetic_fallback: bool = (
        os.getenv("RAG_SYNTHETIC_QUERY_EMBEDDINGS", "0") == "1"
    )
    enable_embedding_warmup: bool = os.getenv("ENABLE_EMBEDDING_WARMUP", "1") == "1"
    enable_generation_warmup: bool = os.getenv("ENABLE_GENERATION_WARMUP", "1") == "1"

    enable_atlas_search: bool = os.getenv("ENABLE_ATLAS_SEARCH", "auto") != "false"
    enable_exact_search_fallback: bool = (
        os.getenv("ENABLE_EXACT_SEARCH_FALLBACK", "true") == "true"
    )
    enable_semantic_search_fallback: bool = (
        os.getenv("ENABLE_SEMANTIC_SEARCH_FALLBACK", "true") == "true"
    )

    enable_intelligent_routing: bool = True
    enable_timeout_processing: bool = True
    enable_auto_background: bool = True

    auto_background_threshold_seconds: int = 8
    timeout_check_interval_seconds: float = 1.0
    min_confidence_for_auto_background: float = 0.6
    min_confidence_for_timeout: float = 0.4
    min_confidence_for_suggestion: float = 0.3

    rag_query_timeout_seconds: float = float(os.getenv("RAG_QUERY_TIMEOUT", "1.2"))
    rag_max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "8000"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "10"))
    rag_max_snippets: int = int(os.getenv("RAG_MAX_SNIPPETS", "5"))

    enable_memory_monitoring: bool = os.getenv("ENABLE_MEMORY_MONITORING", "1") == "1"
    memory_cleanup_threshold: float = float(
        os.getenv("MEMORY_CLEANUP_THRESHOLD", "0.80")
    )

    enable_performance_tracking: bool = (
        os.getenv("ENABLE_PERFORMANCE_TRACKING", "1") == "1"
    )
    enable_telemetry: bool = os.getenv("ENABLE_TELEMETRY", "1") == "1"

    enable_advanced_document_processor: bool = (
        os.getenv("ENABLE_ADVANCED_DOC_PROCESSOR", "1") == "1"
    )
    enable_pdf_processing: bool = os.getenv("SEED_ENABLE_PDF", "1") == "1"
    enable_docx_processing: bool = os.getenv("SEED_ENABLE_DOCX", "1") == "1"
    enable_csv_processing: bool = os.getenv("SEED_ENABLE_CSV", "1") == "1"
    enable_html_processing: bool = os.getenv("SEED_ENABLE_HTML", "1") == "1"
    enable_json_processing: bool = os.getenv("SEED_ENABLE_JSON", "1") == "1"

    seed_dynamic_batch_sizing: bool = os.getenv("SEED_DYNAMIC_BATCH_SIZING", "1") == "1"
    seed_parallel_processing: bool = os.getenv("SEED_PARALLEL_PROCESSING", "1") == "1"
    seed_max_workers: int = int(os.getenv("SEED_MAX_WORKERS", "4"))
    seed_memory_monitoring: bool = os.getenv("SEED_MEMORY_MONITORING", "1") == "1"
    seed_memory_threshold: float = float(os.getenv("SEED_MEMORY_THRESHOLD", "85.0"))

    seed_initial_batch_size: int = int(os.getenv("SEED_BATCH_SIZE", "16"))
    seed_min_batch_size: int = int(os.getenv("SEED_MIN_BATCH_SIZE", "4"))
    seed_max_batch_size: int = int(os.getenv("SEED_MAX_BATCH_SIZE", "32"))

    seed_max_file_size_mb: int = int(os.getenv("SEED_MAX_FILE_SIZE_MB", "50"))
    seed_skip_failed_files: bool = os.getenv("SEED_SKIP_FAILED_FILES", "1") == "1"

    seed_max_retries: int = int(os.getenv("SEED_MAX_RETRIES", "3"))
    seed_retry_delay: float = float(os.getenv("SEED_RETRY_DELAY", "2.0"))

    seed_monitor_index_creation: bool = (
        os.getenv("SEED_MONITOR_INDEX_CREATION", "1") == "1"
    )
    atlas_index_timeout: int = int(os.getenv("ATLAS_INDEX_TIMEOUT", "600"))

    seed_enable_quality_checks: bool = os.getenv("SEED_QUALITY_CHECKS", "1") == "1"
    seed_min_quality_score: float = float(os.getenv("SEED_MIN_QUALITY_SCORE", "0.7"))

    seed_enable_detailed_progress: bool = (
        os.getenv("SEED_DETAILED_PROGRESS", "1") == "1"
    )
    seed_progress_report_frequency: int = int(os.getenv("SEED_PROGRESS_FREQUENCY", "5"))

    seed_incremental_mode: bool = os.getenv("SEED_INCREMENTAL_MODE", "0") == "1"
    seed_force_refresh: bool = os.getenv("SEED_FORCE_REFRESH", "0") == "1"

    def get_effective_embedding_dim(self) -> int:
        if self.use_real_embeddings:
            return self.mongo.embedding_dimension
        else:
            return self.mongo.synthetic_embedding_dimension

    def is_atlas_configured(self) -> bool:
        return bool(self.mongo.atlas_uri and self.enable_atlas_search)

    def get_ai_service_status(self) -> dict:
        return {
            "real_embeddings": self.use_real_embeddings,
            "real_generation": self.use_real_generation,
            "synthetic_fallback": self.use_synthetic_fallback,
            "atlas_search": self.enable_atlas_search,
            "exact_fallback": self.enable_exact_search_fallback,
            "semantic_fallback": self.enable_semantic_search_fallback,
            "embedding_dimension": self.get_effective_embedding_dim(),
            "atlas_configured": self.is_atlas_configured(),
        }

    def get_performance_config(self) -> dict:
        return {
            "memory_monitoring": self.enable_memory_monitoring,
            "performance_tracking": self.enable_performance_tracking,
            "telemetry": self.enable_telemetry,
            "memory_cleanup_threshold": self.memory_cleanup_threshold,
            "rag_query_timeout": self.rag_query_timeout_seconds,
            "auto_background_threshold": self.auto_background_threshold_seconds,
        }

    def get_enhanced_seeding_config(self) -> dict:
        return {
            "advanced_processor": self.enable_advanced_document_processor,
            "file_formats": {
                "pdf": self.enable_pdf_processing,
                "docx": self.enable_docx_processing,
                "csv": self.enable_csv_processing,
                "html": self.enable_html_processing,
                "json": self.enable_json_processing,
            },
            "performance": {
                "parallel_processing": self.seed_parallel_processing,
                "dynamic_batching": self.seed_dynamic_batch_sizing,
                "max_workers": self.seed_max_workers,
                "memory_monitoring": self.seed_memory_monitoring,
            },
            "quality_control": {
                "quality_checks": self.seed_enable_quality_checks,
                "min_quality_score": self.seed_min_quality_score,
            },
            "atlas_features": {
                "monitor_indexes": self.seed_monitor_index_creation,
                "index_timeout": self.atlas_index_timeout,
            },
        }

    def validate_seeding_configuration(self) -> dict:
        issues = []
        warnings = []

        enabled_formats = [
            ("PDF", self.enable_pdf_processing),
            ("DOCX", self.enable_docx_processing),
            ("CSV", self.enable_csv_processing),
            ("HTML", self.enable_html_processing),
            ("JSON", self.enable_json_processing),
        ]

        enabled_count = sum(1 for _, enabled in enabled_formats if enabled)
        if enabled_count == 0:
            issues.append("No file formats enabled for processing")
        elif enabled_count < 3:
            warnings.append(
                f"Only {enabled_count} file formats enabled - consider enabling more for better coverage"
            )

        if self.seed_max_workers > 8:
            warnings.append("High worker count may cause memory issues on some systems")

        if self.seed_max_file_size_mb > 100:
            warnings.append("Large file size limit may cause memory issues")

        if self.seed_min_batch_size >= self.seed_max_batch_size:
            issues.append("Minimum batch size must be less than maximum batch size")

        if self.seed_memory_threshold > 95.0:
            warnings.append("Memory threshold very high - may cause system instability")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "enabled_formats": [name for name, enabled in enabled_formats if enabled],
        }


config = ApplicationConfig(
    scylla=ScyllaConfig(),
    redis=RedisConfig(),
    postgresql=PostgreSQLConfig(),
    mongo=MongoConfig(),
    embedding=EmbeddingConfig(),
    generation=GenerationConfig(),
    atlas_search=AtlasVectorSearchConfig(),
    search=SearchConfig(),
)
