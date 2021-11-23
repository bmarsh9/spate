# Spate

## Build docker
`cp tools/build_all.sh $PWD && bash build_all.sh && rm build_all.sh`

## Start
`docker-compose up -d postgres_db && docker-compose up -d spate_ui && docker-compose up -d spate_poller spate_cron spate_ingress`

## May have to create base-image
`cd docker_image && docker build -t base-python .`

## Stop
`docker-compose down`

## Auth
`admin@example.com:admin`

## Check install  
`curl http://localhost/api/v1/health`

