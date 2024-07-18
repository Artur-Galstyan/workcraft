#!/bin/bash
set -e

# Modify postgresql.conf
echo "shared_preload_libraries = 'pg_cron'" >> /var/lib/postgresql/data/postgresql.conf
echo "cron.database_name = 'workraft'" >> /var/lib/postgresql/data/postgresql.conf

# Add logging configurations
echo "log_statement = 'none'" >> /var/lib/postgresql/data/postgresql.conf
echo "log_min_messages = 'notice'" >> /var/lib/postgresql/data/postgresql.conf
echo "log_min_error_statement = 'error'" >> /var/lib/postgresql/data/postgresql.conf

# Restart PostgreSQL to apply changes
pg_ctl restart
