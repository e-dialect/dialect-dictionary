# For validating already built Web/H5 artifacts on a constrained host.
# The default source-build Dockerfile remains ops/docker/website.Dockerfile.
FROM nginx:1.27-alpine
RUN apk add --no-cache python3
COPY apps/web/dist/ /usr/share/nginx/html/
COPY apps/mobile/dist/build/h5/ /usr/share/nginx/html/mobile/
COPY ops/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ops/docker/nginx.traefik.conf /etc/nginx/nginx.traefik.conf
COPY ops/docker/site-logo.svg ops/docker/website-config.py ops/docker/website-entrypoint.sh /etc/nginx/
COPY apps/backend/hinghwa-dict-backend/HinghwaDict/site_config.py /etc/nginx/site_config.py
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "/etc/nginx/website-entrypoint.sh"]
