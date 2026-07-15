#!/usr/bin/env bash

set -e

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "Running smoke tests against: $BASE_URL"

echo "Testing NGINX root..."
curl -fsS "$BASE_URL/" > /dev/null

#Test the validity of nginx configuration 
#1.response string should contain --> nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
#2.response string should contain --> nginx: configuration file /etc/nginx/nginx.conf test is successful
#otherwise fail and exit

echo "Testing WordPress route..."
WORDPRESS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/wordpress/")
if [[ "$WORDPRESS_STATUS" != "200" && "$WORDPRESS_STATUS" != "301" && "$WORDPRESS_STATUS" != "302" ]]; then
  echo "WordPress route failed with status: $WORDPRESS_STATUS"
  exit 1
fi

echo "Testing PrestaShop route..."
PRESTASHOP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/prestashop/")
if [[ "$PRESTASHOP_STATUS" != "200" && "$PRESTASHOP_STATUS" != "301" && "$PRESTASHOP_STATUS" != "302" ]]; then
  echo "PrestaShop route failed with status: $PRESTASHOP_STATUS"
  exit 1
fi

echo "Smoke tests passed."
