<p align="center">
  <img height="120px" src="https://github.com/bmarsh9/spate/raw/de65a206015f1119db5981f21fc3974b8a8c8c7f/app/static/img/spate_full.PNG" alt="Logo"/>
</p>

Dark Theme            |  White Theme (:zap: BETA)
:-------------------------:|:-------------------------:
![](photos/a7_dash.PNG?raw=true)  |  ![](photos/a7_white.PNG?raw=true)

## Build docker images
`cp tools/build_all.sh $PWD && bash build_all.sh && rm build_all.sh`

## Start docker images
`docker-compose up -d postgres_db && docker-compose up -d spate_ui && docker-compose up -d spate_poller spate_cron spate_ingress`

## May have to create base-image
`cd docker_image && docker build -t base-python .`

## Stop docker images
`docker-compose down`

## Authentication
`admin@example.com:admin`

## Check install  
`curl http://localhost/api/v1/health`

