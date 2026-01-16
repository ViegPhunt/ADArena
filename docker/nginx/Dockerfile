FROM nginx:1.25.1-alpine

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/http.conf.template /etc/nginx/http.conf.template

COPY docker/nginx/proxy_params /etc/nginx/proxy_params
COPY docker/nginx/proxy_params_ws /etc/nginx/proxy_params_ws

COPY frontend/dist /var/www/front

ARG DNS_RESOLVER
ENV DNS_RESOLVER ${DNS_RESOLVER}
RUN envsubst '\${DNS_RESOLVER}' </etc/nginx/http.conf.template >/etc/nginx/http.conf