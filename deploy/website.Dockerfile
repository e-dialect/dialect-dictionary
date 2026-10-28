FROM node:22-bookworm-slim AS web-build
ENV NODE_OPTIONS=--max-old-space-size=1536 UV_THREADPOOL_SIZE=2
WORKDIR /build/web
COPY web/package.json web/yarn.lock ./
RUN test ! -e node_modules && yarn install --frozen-lockfile --non-interactive --network-timeout 60000
COPY web/ ./
RUN yarn build

# Inherit the preceding stage so the two compilers run sequentially.
FROM web-build AS frontends-build
WORKDIR /build/uni-app
COPY uni-app/package.json uni-app/yarn.lock ./
RUN test ! -e node_modules && yarn install --frozen-lockfile --non-interactive --network-timeout 60000
COPY uni-app/ ./
RUN yarn build:h5

FROM nginx:1.27-alpine
RUN apk add --no-cache python3
COPY --from=frontends-build /build/web/dist/ /usr/share/nginx/html/
COPY --from=frontends-build /build/uni-app/dist/build/h5/ /usr/share/nginx/html/mobile/
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/site-logo.svg deploy/website-config.py deploy/website-entrypoint.sh /etc/nginx/
COPY backend/hinghwa-dict-backend/HinghwaDict/site_config.py /etc/nginx/site_config.py
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "/etc/nginx/website-entrypoint.sh"]
