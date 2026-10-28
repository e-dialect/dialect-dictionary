#!/bin/sh
set -eu
case "${PROXY_MODE:-local}" in
  local) ;;
  traefik) cp /etc/nginx/nginx.traefik.conf /etc/nginx/conf.d/default.conf ;;
  *) echo "Invalid PROXY_MODE" >&2; exit 1 ;;
esac
python3 /etc/nginx/website-config.py
exec nginx -g 'daemon off;'
