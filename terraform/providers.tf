provider "proxmox" {
  pm_api_url      = var.proxmox_endpoint
  pm_tls_insecure = true
}