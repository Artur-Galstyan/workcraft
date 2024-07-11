#!/bin/bash

docker build -t workraft-postgres .

docker stop workraft-db && docker rm workraft-db
docker run -d --name workraft-db -p 5433:5432 -e POSTGRES_PASSWORD=mysecretpassword workraft-postgres
