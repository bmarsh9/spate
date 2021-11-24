# install base
FROM ubuntu

# update the operating system:
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
RUN apt install -y python3-pip nano libpq-dev net-tools sudo libssl-dev

# copy the folder to the container:
ADD . /spate

# Define working directory:
WORKDIR /spate

# Install the requirements
RUN pip3 install -r /spate/requirements.txt

# expose tcp port 5000
#EXPOSE 5000

# default command: run the web server
CMD ["/bin/bash","run.sh"]
