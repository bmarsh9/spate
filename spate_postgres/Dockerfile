# install base
FROM ubuntu

# update the operating system:
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/New_York
RUN apt-get update && apt-get install -y tzdata && apt install -y nano sudo postgresql postgresql-contrib

# copy the folder to the container:
ADD . /spate_postgres

# Define working directory:
WORKDIR /spate_postgres

USER postgres

EXPOSE 5432

# Adjust PostgreSQL configuration so that remote connections to the
# database are possible.
RUN echo "host all  all    0.0.0.0/0  md5" >> /etc/postgresql/12/main/pg_hba.conf

# And add ``listen_addresses`` to ``/etc/postgresql/12/main/postgresql.conf``
RUN echo "listen_addresses='*'" >> /etc/postgresql/12/main/postgresql.conf

# default command
CMD ["/bin/bash","/spate_postgres/run.sh"]
