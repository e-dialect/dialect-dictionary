FROM python:3.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ops/docker/requirements.dictionary.lock /tmp/requirements.dictionary.lock
RUN --mount=type=cache,target=/root/.cache/pip pip install --require-hashes -r /tmp/requirements.dictionary.lock && pip check
COPY apps/backend/hinghwa-dict-backend/ /app/
COPY ops/docker/backend-entrypoint.py /app/backend-entrypoint.py
COPY ops/docker/manage-command.py /app/manage-command.py
ENV DJANGO_SETTINGS_MODULE=HinghwaDict.standalone
EXPOSE 8000
ENTRYPOINT ["python", "/app/backend-entrypoint.py"]
