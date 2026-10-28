FROM node:22-bookworm-slim AS web-build
ENV NODE_OPTIONS=--max-old-space-size=1536 UV_THREADPOOL_SIZE=2
WORKDIR /build/web
COPY apps/web/package.json apps/web/yarn.lock ./
RUN test ! -e node_modules && yarn install --frozen-lockfile --non-interactive --network-timeout 60000
COPY apps/web/ ./
RUN yarn build

# Inherit the preceding stage so the two compilers run sequentially.
FROM web-build AS frontends-build
WORKDIR /build/uni-app
COPY apps/mobile/package.json apps/mobile/yarn.lock ./
RUN test ! -e node_modules && yarn install --frozen-lockfile --non-interactive --network-timeout 60000
COPY apps/mobile/ ./
RUN yarn build:h5

FROM nginx:1.27-alpine
RUN apk add --no-cache python3
COPY --from=frontends-build /build/web/dist/ /usr/share/nginx/html/
COPY --from=frontends-build /build/uni-app/dist/build/h5/ /usr/share/nginx/html/mobile/
COPY ops/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY ops/docker/nginx.traefik.conf /etc/nginx/nginx.traefik.conf
COPY ops/docker/site-logo.svg ops/docker/website-config.py ops/docker/website-entrypoint.sh /etc/nginx/
COPY apps/backend/hinghwa-dict-backend/HinghwaDict/site_config.py /etc/nginx/site_config.py
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "/etc/nginx/website-entrypoint.sh"]
