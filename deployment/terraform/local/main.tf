terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Shared network for inter-service communication
resource "docker_network" "chatbot_network" {
  name = "chatbot_network"
  driver = "bridge"
}

# Persistent volumes
resource "docker_volume" "postgres_data" {
  name = "postgres_data"
}

resource "docker_volume" "redis_data" {
  name = "redis_data" 
}

resource "docker_volume" "mongo_data" {
  name = "mongo_data"
}

resource "docker_volume" "mongo_config" {
  name = "mongo_config"
}

resource "docker_volume" "mongo_mongot" {
  name = "mongo_mongot"
}

resource "docker_volume" "scylla_data1" {
  name = "scylla_data1"
}

resource "docker_volume" "scylla_data2" {
  name = "scylla_data2"  
}

resource "docker_volume" "scylla_data3" {
  name = "scylla_data3"
}

# PostgreSQL with pgvector
resource "docker_image" "postgres" {
  name = "pgvector/pgvector:pg15"
}

resource "docker_container" "postgres" {
  image = docker_image.postgres.image_id
  name  = "chatbot-postgres"
  
  env = [
    "POSTGRES_DB=chatbot_app",
    "POSTGRES_USER=chatbot_user", 
    "POSTGRES_PASSWORD=secure_password"
  ]
  
  ports {
    internal = 5432
    external = 5432
  }
  
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U chatbot_user"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

# Redis
resource "docker_image" "redis" {
  name = "redis:6-alpine"
}

resource "docker_container" "redis" {
  image = docker_image.redis.image_id
  name  = "my-redis"
  
  command = ["redis-server", "--appendonly", "yes"]
  
  ports {
    internal = 6379
    external = 6379
  }
  
  volumes {
    volume_name    = docker_volume.redis_data.name
    container_path = "/data"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD", "redis-cli", "ping"]
    interval = "10s"
    timeout  = "5s" 
    retries  = 5
  }
}

# MongoDB Atlas Local
resource "docker_image" "mongodb" {
  name = "mongodb/mongodb-atlas-local:latest"
}

resource "docker_container" "mongodb" {
  image = docker_image.mongodb.image_id
  name  = "mongodb-atlas-local"
  
  hostname = "mongodb-atlas-local"
  
  env = [
    "MONGODB_INITDB_ROOT_USERNAME=root",
    "MONGODB_INITDB_ROOT_PASSWORD=example",
    "MONGODB_REPLICA_SET_NAME=mongodb-atlas-local"
  ]
  
  ports {
    internal = 27017
    external = 27017
  }
  
  volumes {
    volume_name    = docker_volume.mongo_data.name
    container_path = "/data/db"
  }
  
  volumes {
    volume_name    = docker_volume.mongo_config.name  
    container_path = "/data/configdb"
  }
  
  volumes {
    volume_name    = docker_volume.mongo_mongot.name
    container_path = "/data/mongot"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "always"
  
  healthcheck {
    test         = ["CMD-SHELL", "mongosh --eval 'db.runCommand(\"ping\").ok' --quiet"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 5
    start_period = "120s"
  }
}

# ScyllaDB Node 1 (Seed)
resource "docker_image" "scylla" {
  name = "scylladb/scylla:latest"
}

resource "docker_container" "scylla_node1" {
  image = docker_image.scylla.image_id
  name  = "scylla-node1"
  
  command = [
    "--seeds=scylla-node1",
    "--smp", "1", 
    "--memory", "750M",
    "--overprovisioned", "1",
    "--api-address", "0.0.0.0"
  ]
  
  ports {
    internal = 9042
    external = 9042
  }
  
  ports {
    internal = 10000
    external = 10000  
  }
  
  volumes {
    volume_name    = docker_volume.scylla_data1.name
    container_path = "/var/lib/scylla"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout  = "5s"
    retries  = 24
  }
}

# ScyllaDB Node 2
resource "docker_container" "scylla_node2" {
  image = docker_image.scylla.image_id
  name  = "scylla-node2"
  
  command = [
    "--seeds=scylla-node1",
    "--smp", "1",
    "--memory", "750M", 
    "--overprovisioned", "1",
    "--api-address", "0.0.0.0"
  ]
  
  ports {
    internal = 9042
    external = 9043
  }
  
  ports {
    internal = 10000
    external = 10001
  }
  
  volumes {
    volume_name    = docker_volume.scylla_data2.name
    container_path = "/var/lib/scylla"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [docker_container.scylla_node1]
  
  healthcheck {
    test     = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout  = "5s"
    retries  = 12
  }
}

# ScyllaDB Node 3  
resource "docker_container" "scylla_node3" {
  image = docker_image.scylla.image_id
  name  = "scylla-node3"
  
  command = [
    "--seeds=scylla-node1",
    "--smp", "1",
    "--memory", "750M",
    "--overprovisioned", "1", 
    "--api-address", "0.0.0.0"
  ]
  
  ports {
    internal = 9042
    external = 9044
  }
  
  ports {
    internal = 10000
    external = 10002
  }
  
  volumes {
    volume_name    = docker_volume.scylla_data3.name
    container_path = "/var/lib/scylla"
  }
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [docker_container.scylla_node2]
  
  healthcheck {
    test     = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout  = "5s"
    retries  = 12
  }
}

# API Gateway Service
resource "docker_image" "api_gateway" {
  name = "multidb-api-gateway:latest"
  build {
    context    = "../../"
    dockerfile = "Dockerfile.api-gateway"
  }
}

resource "docker_container" "api_gateway" {
  image = docker_image.api_gateway.image_id
  name  = "multidb-api-gateway"
  
  ports {
    internal = 8000
    external = 8000
  }
  
  env = [
    "POSTGRES_DSN=postgresql+asyncpg://chatbot_user:secure_password@chatbot-postgres:5432/chatbot_app",
    "REDIS_URL=redis://my-redis:6379/0",
    "SEARCH_SERVICE_URL=http://search-service:8001",
    "EMBEDDING_SERVICE_URL=http://embedding-service:8002", 
    "GENERATION_SERVICE_URL=http://generation-service:8003",
    "API_GATEWAY_PORT=8000"
  ]
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.postgres,
    docker_container.redis,
    docker_container.search_service,
    docker_container.embedding_service,
    docker_container.generation_service
  ]
  
  healthcheck {
    test     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

# Search Service
resource "docker_image" "search_service" {
  name = "multidb-search-service:latest"
  build {
    context    = "../../"
    dockerfile = "Dockerfile.search-service"
  }
}

resource "docker_container" "search_service" {
  image = docker_image.search_service.image_id
  name  = "multidb-search-service"
  
  ports {
    internal = 8001
    external = 8001
  }
  
  env = [
    "POSTGRES_DSN=postgresql+asyncpg://chatbot_user:secure_password@chatbot-postgres:5432/chatbot_app",
    "REDIS_URL=redis://my-redis:6379/0",
    "EMBEDDING_SERVICE_URL=http://embedding-service:8002",
    "SEARCH_SERVICE_PORT=8001"
  ]
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.postgres,
    docker_container.redis,
    docker_container.embedding_service
  ]
  
  healthcheck {
    test     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

# Embedding Service
resource "docker_image" "embedding_service" {
  name = "multidb-embedding-service:latest"
  build {
    context    = "../../"
    dockerfile = "Dockerfile.embedding-service"
  }
}

resource "docker_container" "embedding_service" {
  image = docker_image.embedding_service.image_id
  name  = "multidb-embedding-service"
  
  ports {
    internal = 8002
    external = 8002
  }
  
  env = [
    "EMBEDDING_SERVICE_PORT=8002"
  ]
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

# Generation Service
resource "docker_image" "generation_service" {
  name = "multidb-generation-service:latest"
  build {
    context    = "../../"
    dockerfile = "Dockerfile.generation-service"
  }
}

resource "docker_container" "generation_service" {
  image = docker_image.generation_service.image_id
  name  = "multidb-generation-service"
  
  ports {
    internal = 8003
    external = 8003
  }
  
  env = [
    "GENERATION_SERVICE_PORT=8003"
  ]
  
  networks_advanced {
    name = docker_network.chatbot_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD-SHELL", "curl -f http://localhost:8003/health || exit 1"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}