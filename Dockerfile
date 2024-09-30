FROM postgres:latest

RUN apt-get update && \
    apt-get install -y postgresql-17-cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use WK_DB_NAME environment variable
ENV WK_DB_NAME=workraft
ENV POSTGRES_DB=${WK_DB_NAME}

COPY init-pg-cron.sh /docker-entrypoint-initdb.d/init-pg-cron.sh
RUN chmod +x /docker-entrypoint-initdb.d/init-pg-cron.sh && \
    chown postgres:postgres /docker-entrypoint-initdb.d/init-pg-cron.sh

# Ensure pg_cron is loaded at startup and set the correct database
RUN echo "shared_preload_libraries = 'pg_cron'" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "cron.database_name = '${WK_DB_NAME}'" >> /usr/share/postgresql/postgresql.conf.sample

CMD ["postgres"]
