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
```


## Network Isolation in the Docker-Container Architecture

Only NGINX exposes a host port. WordPress, PrestaShop, and both databases are reachable only inside Docker networks.

This supports the single-entry-point architecture.

### Network Isolation Validation

```text
nginx-proxy    0.0.0.0:8080->80/tcp
wordpress      80/tcp only, no host mapping
prestashop     80/tcp only, no host mapping
wordpress-db   3306/tcp only, no host mapping
prestashop-db  3306/tcp only, no host mapping
```

## Persistence in the Docker-Container Architecture

The CMS and database containers use Docker volumes. 

### Persistence Validation

After restarting containers, the services remain reachable and data directories remain mounted through persistent volumes.
Later, after installing WordPress/PrestaShop, create data and verify it survives container recreation
