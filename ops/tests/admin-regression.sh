#!/usr/bin/env bash
# Synthetic, offline tests. Requires an already cached backend image; never pulls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backend"])' "$ROOT/ops/docker/validated-images.json")"
if [ "$#" -eq 0 ]; then
  set -- website HinghwaDict word.test_resource_packages word.test_import_media_gate word.test_legacy_import_alias word.test_private_bulk
fi
docker run --rm --pull never --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,size=256m --tmpfs /data:rw,size=256m --tmpfs /app:rw,size=128m \
  --mount "type=bind,src=$ROOT/apps/backend/hinghwa-dict-backend,dst=/src,readonly" \
  --mount "type=bind,src=$ROOT/config,dst=/config,readonly" \
  -e DJANGO_SETTINGS_MODULE=HinghwaDict.standalone \
  -e DICTIONARY_CONFIG=/config/examples/coast.json -e DICTIONARY_DATA_DIR=/data \
  -e SECRET_KEY=synthetic-regression-only-not-production \
  -e JWT_KEY=synthetic-regression-only-not-production -e DEBUG=False \
  -e ENABLE_BACKGROUND_SCHEDULER=False -e SEMANTIC_SEARCH_ENABLED=False \
  --entrypoint /bin/sh "$IMAGE" -c '
    set -eu
    # Separate commands preserve source tar failures under POSIX sh set -e.
    tar -C /src --exclude=".env*" --exclude="*.sqlite3" --exclude="logs" \
      --exclude="media" --exclude="__pycache__" -cf /tmp/backend-source.tar .
    tar -xf /tmp/backend-source.tar -C /app
    rm /tmp/backend-source.tar
    mkdir -p /app/logs
    cd /app
    python manage.py test "$@" --noinput
    python manage.py makemigrations website --check --dry-run
  ' sh "$@"
