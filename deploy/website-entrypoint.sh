#!/bin/sh
set -eu
python3 /etc/nginx/website-config.py
exec nginx -g 'daemon off;'
