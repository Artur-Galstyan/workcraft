FROM postgres:latest

RUN apt-get update && apt-get install -y postgresql-16-cron

# Set default database name
ENV POSTGRES_DB workraft

# Copy custom initialization scripts
COPY init-pg-cron.sh /docker-entrypoint-initdb.d/

# Set execute permissions for the script
RUN chmod +x /docker-entrypoint-initdb.d/init-pg-cron.sh

CMD ["postgres"]
