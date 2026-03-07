variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "rg-ai-analyst-prod"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "West Europe"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "acr_name" {
  description = "Azure Container Registry name (globally unique, alphanumeric)"
  type        = string
  default     = "acraianalyst"
}

variable "storage_account_name" {
  description = "Storage account name (globally unique, lowercase, 3-24 chars)"
  type        = string
  default     = "staianalystprod"
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}
