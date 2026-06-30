# Manual Docker Proof of Concept

## Goal

This manual Docker POC proves that the web services platform can run with isolated containers,
Docker networks, persistent volumes, and NGINX reverse proxy routing before moving to Docker Compose.

## Architecture

```text
User
  |
  v
NGINX reverse proxy
  |
  |-- /wordpress/  -> WordPress container -> WordPress DB container
  |
  |-- /prestashop/ -> PrestaShop container -> PrestaShop DB container


## Network Isolation Validation

Only NGINX exposes a host port. WordPress, PrestaShop, and both databases are reachable only inside Docker networks.

This supports the single-entry-point architecture.
