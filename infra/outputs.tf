output "api_url" {
  description = "Public URL of the FastAPI backend"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "app_url" {
  description = "Public URL of the Streamlit frontend"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}
