# install base
FROM ubuntu

# update the operating system:
RUN apt-get update && apt-get install -y apt-transport-https
RUN apt install -y python3-pip nano net-tools sudo libpq-dev

# copy the folder to the container:
ADD . /spate_poller

# Define working directory:
WORKDIR /spate_poller

# Install the requirements
RUN pip3 install -r /spate_poller/requirements.txt

# default command: run the web server
CMD ["python3","/spate_poller/app.py"]

