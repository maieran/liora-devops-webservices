#!/usr/bin/env bash
set -euo pipefail

PUBLIC_IP="$(curl -fsS https://checkip.amazonaws.com | tr -d '\n')"
export SERVER_HOST="${PUBLIC_IP}:8080"

echo "Using server host: ${SERVER_HOST}"

docker compose config --quiet
docker compose up -d --build

echo "Waiting for PrestaShop database..."
until docker compose exec -T prestashop-db \
  mysqladmin ping \
  -h localhost \
  -u root \
  -p"${PRESTASHOP_DB_ROOT_PASSWORD:-rootpass}" \
  --silent >/dev/null 2>&1
do
  sleep 3
done

docker compose exec -T prestashop-db \
  mysql \
  -u"${PRESTASHOP_DB_USER:-prestashop}" \
  -p"${PRESTASHOP_DB_PASSWORD:-prestashoppass}" \
  "${PRESTASHOP_DB_NAME:-prestashop}" <<SQL
UPDATE ps_shop_url
SET
  domain = '${SERVER_HOST}',
  domain_ssl = '${SERVER_HOST}',
  physical_uri = '/',
  virtual_uri = ''
WHERE main = 1;

UPDATE ps_configuration
SET value = '${SERVER_HOST}'
WHERE name IN ('PS_SHOP_DOMAIN', 'PS_SHOP_DOMAIN_SSL');
SQL

docker compose exec -T prestashop sh -lc '
rm -rf /var/www/html/var/cache/prod/* /var/www/html/var/cache/dev/*
'

docker compose restart prestashop
sleep 15

docker compose up -d --build --force-recreate nginx

echo
echo "Deployment complete:"
echo "WordPress:  http://${SERVER_HOST}/wordpress/"
echo "PrestaShop: http://${SERVER_HOST}/prestashop/"