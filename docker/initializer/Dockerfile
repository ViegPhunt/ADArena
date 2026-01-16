FROM adarena-base:latest

COPY backend /app

COPY ./docker/initializer/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]