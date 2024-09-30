#!/bin/bash
set -e

# Function to run SQL commands
psql_command() {
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$1" --command "$2"
}

# Wait for PostgreSQL to be ready
until psql_command "$POSTGRES_DB" "SELECT 1" > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# Update postgresql.conf with the correct cron.database_name
echo "cron.database_name = '$POSTGRES_DB'" >> $PGDATA/postgresql.conf

# Restart PostgreSQL to apply the new configuration
pg_ctl -D "$PGDATA" -m fast -w restart

# Wait for PostgreSQL to be ready again
until psql_command "$POSTGRES_DB" "SELECT 1" > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL to restart..."
  sleep 1
done

# Add logging configurations
psql_command "$POSTGRES_DB" "ALTER SYSTEM SET log_statement TO 'none';"
psql_command "$POSTGRES_DB" "ALTER SYSTEM SET log_min_messages TO 'notice';"
psql_command "$POSTGRES_DB" "ALTER SYSTEM SET log_min_error_statement TO 'error';"

# Enable pg_cron extension
psql_command "$POSTGRES_DB" "CREATE EXTENSION IF NOT EXISTS pg_cron;"

# Reload PostgreSQL configuration
psql_command "$POSTGRES_DB" "SELECT pg_reload_conf();"

echo "pg_cron initialization completed for database: $POSTGRES_DB"
