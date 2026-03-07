terraform {
  required_version = ">= 1.8.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "tfstateanalyst"
    container_name       = "tfstate"
    key                  = "ai-analyst.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# ── Resource Group ─────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# ── Container Registry ─────────────────────────────────────────────────────────
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.tags
}

# ── Log Analytics ──────────────────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-ai-analyst-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# ── Container Apps Environment ─────────────────────────────────────────────────
resource "azurerm_container_app_environment" "main" {
  name                       = "cae-ai-analyst-${var.environment}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# ── Storage Account ────────────────────────────────────────────────────────────
resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags
}

resource "azurerm_storage_share" "uploads" {
  name                 = "uploads"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 10
}

resource "azurerm_storage_share" "outputs" {
  name                 = "outputs"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 20
}

# ── Link Storage to Container App Environment ──────────────────────────────────
resource "azurerm_container_app_environment_storage" "uploads" {
  name                         = "uploads"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.uploads.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_container_app_environment_storage" "outputs" {
  name                         = "outputs"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.outputs.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

# ── Container App: API ─────────────────────────────────────────────────────────
resource "azurerm_container_app" "api" {
  name                         = "ca-ai-analyst-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  depends_on = [
    azurerm_container_app_environment_storage.uploads,
    azurerm_container_app_environment_storage.outputs,
  ]

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  secret {
    name  = "openai-api-key"
    value = var.openai_api_key
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "api"
      image  = "${azurerm_container_registry.acr.login_server}/ai-analyst-api:latest"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name  = "UPLOADS_DIR"
        value = "/data/uploads"
      }
      env {
        name  = "OUTPUTS_DIR"
        value = "/data/outputs"
      }

      volume_mounts {
        name = "uploads-vol"
        path = "/data/uploads"
      }
      volume_mounts {
        name = "outputs-vol"
        path = "/data/outputs"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
    }

    volume {
      name         = "uploads-vol"
      storage_type = "AzureFile"
      storage_name = "uploads"
    }

    volume {
      name         = "outputs-vol"
      storage_type = "AzureFile"
      storage_name = "outputs"
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ── Container App: Streamlit App ───────────────────────────────────────────────
resource "azurerm_container_app" "app" {
  name                         = "ca-ai-analyst-app-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  depends_on = [azurerm_container_app.api]

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "app"
      image  = "${azurerm_container_registry.acr.login_server}/ai-analyst-app:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "API_BASE_URL"
        value = "https://${azurerm_container_app.api.ingress[0].fqdn}/api/v1"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8501
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

locals {
  tags = {
    project     = "ai-data-analyst-agent"
    environment = var.environment
    owner       = "Katiadje"
    managed_by  = "terraform"
  }
}
