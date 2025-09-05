"""
Environment loader utility for AI services
Provides consistent environment loading across all Python AI services
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_environment_config() -> Dict[str, Any]:
    """Load the environment configuration from YAML file"""
    project_root = Path(__file__).parent.parent.parent.parent
    config_file = project_root / "config" / "environments.yaml"
    
    if not config_file.exists():
        logger.warning(f"Environment config not found at {config_file}")
        return {"environments": {}, "default_environment": "development"}
    
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load environment config: {e}")
        return {"environments": {}, "default_environment": "development"}

def detect_environment() -> str:
    """Detect which environment we should be running in based on config rules"""
    config = load_environment_config()
    
    # Apply detection rules in priority order
    detection_rules = config.get("detection_rules", [])
    for rule in detection_rules:
        env_var = rule.get("env_var")
        if not env_var:
            continue
            
        env_value = os.getenv(env_var)
        if not env_value:
            continue
            
        # Check if rule has specific value requirement
        if "value" in rule:
            if env_value == rule["value"]:
                return rule.get("maps_to", env_value.lower())
        else:
            # Direct environment variable value
            env_lower = env_value.lower()
            if env_lower in ["demo_v1", "demo"]:
                return "demo"
            elif env_lower in ["development", "dev"]:
                return "development"
            elif env_lower in ["production", "prod"]:
                return "production"
            elif env_lower in ["testing", "test"]:
                return "testing"
    
    # Return default environment
    return config.get("default_environment", "development")

def load_environment_file(env_type: str) -> int:
    """Load environment file for the specified environment type"""
    config = load_environment_config()
    environments = config.get("environments", {})
    
    env_config = environments.get(env_type)
    if not env_config:
        logger.error(f"No configuration found for environment: {env_type}")
        return 0
    
    env_file_path = env_config.get("env_file")
    if not env_file_path:
        logger.info(f"✅ {env_type.title()} environment - using system variables")
        return 0
    
    # Find the actual file path
    project_root = Path(__file__).parent.parent.parent.parent
    full_path = project_root / env_file_path
    
    if not full_path.exists():
        logger.error(f"Environment file not found: {full_path}")
        return 0
    
    try:
        # Load with override=True to ensure environment-specific settings take precedence
        load_dotenv(full_path, override=True)
        logger.info(f"✅ Loaded {env_type} environment from {env_file_path}")
        return 1
    except Exception as e:
        logger.error(f"Failed to load {env_type} environment: {e}")
        return 0

def load_environment(env_type: Optional[str] = None) -> int:
    """Main environment loader - detects and loads appropriate config"""
    if env_type is None:
        env_type = detect_environment()
    
    logger.info(f"🔧 Detected environment: {env_type}")
    return load_environment_file(env_type)

# Legacy functions for backward compatibility
def load_demo_environment(override: bool = False) -> int:
    """Legacy function - use load_environment() instead"""
    return load_environment_file("demo")

def is_demo_mode() -> bool:
    """Check if we're running in demo mode"""
    return detect_environment() == "demo"

def get_demo_service_url(service_name: str) -> Optional[str]:
    """Get the demo URL for a service if in demo mode"""
    if not is_demo_mode():
        return None
    
    port_map = {
        "search": "8001",
        "chat-history": "8002",
        "embedding": "8005", 
        "generation": "8006",
        "content-safety": "8007",
        "auth": "8080",
        "audit": "8084",
        "consent": "8085",
        "api-gateway": "8090",
    }
    
    port = port_map.get(service_name)
    return f"http://localhost:{port}" if port else None

def get_demo_database_urls() -> dict:
    """Get all demo database URLs if in demo mode"""
    if not is_demo_mode():
        return {}
    
    return {
        "postgres": os.getenv("DATABASE_URL", "postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app"),
        "mongodb": os.getenv("MONGODB_URL", "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"),
        "redis": f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6380')}",
        "scylla": {
            "hosts": os.getenv("SCYLLA_HOSTS", "localhost:9045,localhost:9046,localhost:9047").split(","),
            "keyspace": os.getenv("SCYLLA_KEYSPACE", "demo_v1_chatbot_ks")
        }
    }