# For validating already built Web/H5 artifacts on a constrained host.
# The default source-build Dockerfile remains deploy/website.Dockerfile.
FROM nginx:1.27-alpine
RUN apk add --no-cache python3
COPY web/dist/ /usr/share/nginx/html/
COPY uni-app/dist/build/h5/ /usr/share/nginx/html/mobile/
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/site-logo.svg deploy/website-config.py deploy/website-entrypoint.sh /etc/nginx/
COPY backend/hinghwa-dict-backend/HinghwaDict/site_config.py /etc/nginx/site_config.py
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "/etc/nginx/website-entrypoint.sh"]
