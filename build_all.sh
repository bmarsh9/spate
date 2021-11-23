
docker build -t spate-ui .
cd spate_poller
docker build -t spate-poller .
cd ..
cd spate_cron
docker build -t spate-cron .
cd ..
cd spate_ingress
docker build -t spate-ingress .
cd ..
