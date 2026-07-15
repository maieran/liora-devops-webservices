#!/bin/bash

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "Starting health checks..."
echo "Base URL: $BASE_URL"
echo

check_url() {
    local service_name="$1"
    local url="$2"

    echo "Checking $service_name..."

    if curl -fLsS "$url" > /dev/null; then
        echo "$service_name is healthy"
    else
        echo "$service_name health check failed: $url"
        exit 1
    fi
}

check_url "Nginx" "$BASE_URL/health"
check_url "WordPress" "$BASE_URL/wordpress/"
check_url "PrestaShop" "$BASE_URL/prestashop/"

echo
echo "All health checks completed successfully."