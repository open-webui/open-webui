#!/bin/sh
exec /app/nginx_binary/nginx -c /app/gpt-oi-web/nginx/nginx.conf -g 'daemon off;'
