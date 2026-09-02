# HTTPS / TLS Setup

This document describes the HTTPS implementation for the Liora Kubernetes
development environment.

The goal of this feature is to expose the application over HTTPS on port 443
without breaking the existing internal Kubernetes services or the previous
NodePort-based setup.

## Architecture

HTTPS is terminated by the K3s Traefik Ingress Controller.

Request flow:

```text
Browser
  |
  | HTTPS :443
  v
Traefik Ingress
  |
  | HTTP inside the cluster
  v
Nginx
  |
  +--> PrestaShop
  |
  +--> WordPress

TLS is terminated at Traefik. Nginx and the application containers continue
to communicate internally over HTTP.

This avoids adding certificates directly to the Nginx, WordPress or
PrestaShop containers.

Kubernetes HTTPS Configuration

The Helm chart contains an optional Ingress configuration.

Default configuration in values.yaml:  
nginx:
  ingress:
    enabled: false
    className: traefik
    tls:
      enabled: false
      secretName: liora-tls

HTTPS is enabled for the development environment in values-dev.yaml:    
nginx:
  ingress:
    enabled: true
    tls:
      enabled: true
      secretName: liora-tls  

The Ingress forwards all external requests to nginx-service.

The application routes remain:
 /            -> PrestaShop
/wordpress/  -> WordPress
/health      -> Nginx health endpoint

TLS Certificate

The development environment currently uses a self-signed TLS certificate.

The certificate and private key are created locally and must NOT be committed
to Git.

The repository ignores the local TLS directory: tls/*

Example certificate generation:
mkdir -p tls

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout tls/liora.key \
  -out tls/liora.crt \
  -subj "/CN=liora.local/O=Liora DevOps"

Create the Kubernetes TLS Secret:
kubectl create secret tls liora-tls \
  --cert=tls/liora.crt \
  --key=tls/liora.key \
  -n liora-dev

Verify it:
kubectl get secret liora-tls -n liora-dev

Expected type:
kubernetes.io/tls

Nginx Forwarded Headers

Because TLS is terminated by Traefik, Nginx receives HTTP traffic internally.

To allow WordPress and PrestaShop to detect the original external protocol,
Nginx preserves the forwarded protocol and port headers.

The Nginx configuration uses:
X-Forwarded-Proto
X-Forwarded-Port
X-Forwarded-Host

This allows the applications to correctly generate HTTPS URLs even though
communication between Traefik and Nginx remains HTTP.

A fallback is kept for the previous NodePort setup.

PrestaShop HTTPS Configuration

PrestaShop previously used:
PS_DOMAIN=<PUBLIC_HOST>:30080
PS_ENABLE_SSL=0

This caused PrestaShop to redirect HTTPS requests back to the old NodePort.

The Helm deployment is now conditional.

When Ingress and TLS are enabled:
PS_ENABLE_SSL=1
PS_DOMAIN=<PUBLIC_HOST>

When TLS is disabled:
PS_ENABLE_SSL=0
PS_DOMAIN=<PUBLIC_HOST>:<NGINX_NODE_PORT>

This preserves backward compatibility with the previous NodePort setup.

Helm Deployment

Validate the Helm chart first:
helm lint ./helm/liora -f helm/liora/values-dev.yaml

Render the chart locally if needed:
helm template liora-dev ./helm/liora \
  -f helm/liora/values-dev.yaml

Deploy the development environment:
helm upgrade --install liora-dev \
  ./helm/liora \
  --namespace liora-dev \
  -f helm/liora/values-dev.yaml \
  --set prestashop.publicHost=10.10.10.11 \
  --set networkPolicy.enabled=true \
  --server-side=true \
  --force-conflicts \
  --wait \
  --timeout 6m

  --server-side=true and --force-conflicts were required because the
PrestaShop Deployment contained a field that had previously been managed by
kubectl-client-side-apply.

Verify the release:
helm status liora-dev -n liora-dev

Verify the Ingress

Check the Ingress:
kubectl get ingress -n liora-dev
Expected ports:80, 443

Detailed information:
kubectl describe ingress liora-ingress -n liora-dev

Verify Traefik:
kubectl get svc -n kube-system | grep traefik
Traefik should expose port 443.

Command-Line HTTPS Tests

Nginx health endpoint: 
curl -k https://10.10.10.11/health
curl -k -I https://10.10.10.11/
curl -k -IL \
  https://10.10.10.11/men/1-1-hummingbird-printed-t-shirt.html   

curl -k -I https://10.10.10.11/wordpress/

Browser Testing from a Local Mac

10.10.10.11 is an internal Proxmox/Kubernetes IP.

A normal browser on a local workstation usually cannot access this address
directly.

For browser testing, create an SSH SOCKS tunnel through the Jenkins VM.

Terminal 1 - Keep the SSH tunnel open

Run this on the local Mac:
ssh -N -D 127.0.0.1:1080 \
  -p 2222 \
  devops@62.210.90.102

Enter the SSH password when requested.

This terminal must remain open while testing.

Because -N is used, no remote shell prompt is shown after the connection is
established.

Terminal 2 - Start a dedicated Chrome instance

Run:  
open -na "Google Chrome" --args \
  --user-data-dir=/tmp/liora-chrome \
  --proxy-server="socks5://127.0.0.1:1080"

Use this Chrome window for the Liora tests.

A normal Chrome window does not use this SOCKS proxy and therefore may not be
able to access 10.10.10.11.

Only two terminals are required:
Terminal 1 -> SSH SOCKS tunnel, stays open
Terminal 2 -> starts the dedicated Chrome instance
After Chrome has started, Terminal 2 can be closed.
Terminal 1 must remain open during testing.

