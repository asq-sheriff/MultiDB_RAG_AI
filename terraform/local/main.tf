# Lilo_EmotionalAI_Backend Local Development Environment
# Infrastructure-as-Code using Terraform + Docker
# ================================================

terraform {
  required_version = ">= 1.0"
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

# Variables
variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default     = "secure_password"
}

variable "mongo_password" {
  description = "MongoDB password"
  type        = string
  sensitive   = true
  default     = "example"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "multidb-chatbot"
}

# Shared Docker Network
resource "docker_network" "multidb_network" {
  name = "${var.project_name}-network"
  driver = "bridge"
  
  ipam_config {
    subnet = "172.20.0.0/16"
  }

  labels {
    label = "project"
    value = var.project_name
  }
}

# Persistent Volumes
resource "docker_volume" "postgres_data" {
  name = "${var.project_name}-postgres-data"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "redis_data" {
  name = "${var.project_name}-redis-data"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "mongo_data" {
  name = "${var.project_name}-mongo-data"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "mongo_config" {
  name = "${var.project_name}-mongo-config"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "mongo_mongot" {
  name = "${var.project_name}-mongo-mongot"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "scylla_data1" {
  name = "${var.project_name}-scylla-data1"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "scylla_data2" {
  name = "${var.project_name}-scylla-data2"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

resource "docker_volume" "scylla_data3" {
  name = "${var.project_name}-scylla-data3"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

# PostgreSQL Database
resource "docker_container" "postgres" {
  name  = "${var.project_name}-postgres"
  image = "pgvector/pgvector:pg15"
  
  env = [
    "POSTGRES_DB=chatbot_app",
    "POSTGRES_USER=chatbot_user",
    "POSTGRES_PASSWORD=${var.postgres_password}"
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
    name = docker_network.multidb_network.name
    aliases = ["postgres-db"]
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test = ["CMD-SHELL", "pg_isready -U chatbot_user"]
    interval = "10s"
    timeout = "5s"
    retries = 5
  }

  labels {
    label = "project"
    value = var.project_name
  }
}

# Redis Cache
resource "docker_container" "redis" {
  name  = "${var.project_name}-redis"
  image = "redis:6-alpine"
  
  ports {
    internal = 6379
    external = 6379
  }
  
  volumes {
    volume_name    = docker_volume.redis_data.name
    container_path = "/data"
  }
  
  networks_advanced {
    name = docker_network.multidb_network.name
    aliases = ["redis-cache"]
  }
  
  restart = "unless-stopped"
  
  command = ["redis-server", "--appendonly", "yes"]
  
  healthcheck {
    test = ["CMD", "redis-cli", "ping"]
    interval = "10s"
    timeout = "5s"
    retries = 5
  }

  labels {
    label = "project"
    value = var.project_name
  }
}

# MongoDB Atlas Local
resource "docker_container" "mongodb" {
  name  = "${var.project_name}-mongodb"
  image = "mongodb/mongodb-atlas-local:latest"
  
  hostname = "mongodb-atlas-local"
  
  env = [
    "MONGODB_INITDB_ROOT_USERNAME=root",
    "MONGODB_INITDB_ROOT_PASSWORD=${var.mongo_password}",
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
    name = docker_network.multidb_network.name
    aliases = ["mongodb-atlas"]
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test = ["CMD-SHELL", "mongosh --eval 'db.runCommand(\"ping\").ok' --quiet"]
    interval = "30s"
    timeout = "10s"
    retries = 5
    start_period = "120s"
  }

  labels {
    label = "project"
    value = var.project_name
  }
}

# ScyllaDB Node 1 (Seed Node)
resource "docker_container" "scylla_node1" {
  name  = "${var.project_name}-scylla-node1"
  image = "scylladb/scylla:latest"
  
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
    name = docker_network.multidb_network.name
    aliases = ["scylla-node1"]
  }
  
  restart = "unless-stopped"
  
  command = ["--seeds=scylla-node1", "--smp", "1", "--memory", "750M", "--overprovisioned", "1", "--api-address", "0.0.0.0"]
  
  healthcheck {
    test = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout = "5s"
    retries = 24
  }

  labels {
    label = "project"
    value = var.project_name
  }
}

# ScyllaDB Node 2
resource "docker_container" "scylla_node2" {
  name  = "${var.project_name}-scylla-node2"
  image = "scylladb/scylla:latest"
  
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
    name = docker_network.multidb_network.name
    aliases = ["scylla-node2"]
  }
  
  restart = "unless-stopped"
  
  command = ["--seeds=scylla-node1", "--smp", "1", "--memory", "750M", "--overprovisioned", "1", "--api-address", "0.0.0.0"]
  
  healthcheck {
    test = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout = "5s"
    retries = 12
  }

  # Wait for node1 to be healthy
  depends_on = [docker_container.scylla_node1]

  labels {
    label = "project"
    value = var.project_name
  }
}

# ScyllaDB Node 3
resource "docker_container" "scylla_node3" {
  name  = "${var.project_name}-scylla-node3"
  image = "scylladb/scylla:latest"
  
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
    name = docker_network.multidb_network.name
    aliases = ["scylla-node3"]
  }
  
  restart = "unless-stopped"
  
  command = ["--seeds=scylla-node1", "--smp", "1", "--memory", "750M", "--overprovisioned", "1", "--api-address", "0.0.0.0"]
  
  healthcheck {
    test = ["CMD-SHELL", "nodetool status | grep -w 'UN'"]
    interval = "10s"
    timeout = "5s"
    retries = 12
  }

  # Wait for node2 to be healthy
  depends_on = [docker_container.scylla_node2]

  labels {
    label = "project"
    value = var.project_name
  }
}

# Outputs
output "network_name" {
  description = "Docker network name for inter-service communication"
  value       = docker_network.multidb_network.name
}

output "postgres_connection" {
  description = "PostgreSQL connection details"
  value = {
    host     = "localhost"
    port     = 5432
    database = "chatbot_app"
    user     = "chatbot_user"
  }
  sensitive = true
}

output "redis_connection" {
  description = "Redis connection details"
  value = {
    host = "localhost"
    port = 6379
  }
}

output "mongodb_connection" {
  description = "MongoDB connection details"
  value = {
    host = "localhost"
    port = 27017
  }
}

output "scylla_nodes" {
  description = "ScyllaDB cluster node details"
  value = {
    node1 = "localhost:9042"
    node2 = "localhost:9043"  
    node3 = "localhost:9044"
  }
}