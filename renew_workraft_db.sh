#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create a .env file with the required variables."
    exit 1
fi

# Load environment variables
source .env

# Check if required variables are set
required_vars=("WK_DB_HOST" "WK_DB_PORT" "WK_DB_USER" "WK_DB_PASS" "WK_DB_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set. Please check your .env file."
        exit 1
    fi
done

# Build the Docker image
docker build -t workraft-postgres .

# Check if container is running and stop it
if docker ps -a | grep -q workraft-db; then
    echo "Stopping and removing existing workraft-db container..."
    docker stop workraft-db
    docker rm workraft-db
fi

# Run the Docker container with environment variables
docker run -d \
    --name workraft-db \
    -p "${WK_DB_PORT}:5432" \
    -e POSTGRES_USER="${WK_DB_USER}" \
    -e POSTGRES_PASSWORD="${WK_DB_PASS}" \
    -e POSTGRES_DB="${WK_DB_NAME}" \
    -e WK_DB_HOST="${WK_DB_HOST}" \
    workraft-postgres

echo "PostgreSQL container 'workraft-db' is now running."
