#!/bin/bash

set -u

BASE_URL="${BASE_URL:-http://localhost:8080}"
FAILED=0

echo "Starting smoke tests..."
echo "Base URL: $BASE_URL"
echo

check_route() {
    local name="$1"
    local path="$2"
    local url="${BASE_URL}${path}"
    local status

    echo "Testing $name: $url"

    status="$(curl -sS -o /dev/null -w "%{http_code}" "$url")"

    case "$status" in
        200|301|302)
            echo "$name passed with HTTP $status"
            ;;
        *)
            echo "$name failed with HTTP $status"
            FAILED=1
            ;;
    esac

    echo
}

check_route "Nginx" "/health"
check_route "WordPress" "/wordpress/"
check_route "PrestaShop" "/prestashop/"

if [ "$FAILED" -ne 0 ]; then
    echo "One or more smoke tests failed."
    exit 1
fi

echo "All smoke tests passed."