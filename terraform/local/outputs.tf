# Terraform Outputs for Local Development
# ========================================

output "connection_summary" {
  description = "Summary of all service connections"
  value = <<-EOT
  
  🔗 MultiDB-Chatbot Local Development Connections
  ================================================
  
  PostgreSQL:  localhost:5432
  Redis:       localhost:6379  
  MongoDB:     localhost:27017
  ScyllaDB:    localhost:9042 (node1), 9043 (node2), 9044 (node3)
  
  Network:     ${docker_network.multidb_network.name}
  
  🔐 Credentials are stored in terraform.tfvars (not in Git)
  
  EOT
}

output "terraform_commands" {
  description = "Common Terraform commands for this environment"
  value = <<-EOT
  
  📋 Common Commands:
  ===================
  
  terraform init          # Initialize Terraform
  terraform plan          # Preview changes
  terraform apply         # Create infrastructure  
  terraform destroy       # Remove all resources
  terraform refresh       # Update state
  terraform output        # Show connection details
  
  EOT
}