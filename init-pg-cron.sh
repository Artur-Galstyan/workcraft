#!/bin/bash
set -e

# Modify postgresql.conf
echo "shared_preload_libraries = 'pg_cron'" >> /var/lib/postgresql/data/postgresql.conf
echo "cron.database_name = 'workraft'" >> /var/lib/postgresql/data/postgresql.conf

# Restart PostgreSQL to apply changes
pg_ctl restart
