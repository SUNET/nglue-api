FROM python:3.11-bullseye

MAINTAINER Kushal Das <kushal@sunet.se>


RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y locales redis

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8

ENV LANG en_US.UTF-8

COPY docker/setup.sh /usr/sbin/setup.sh

# Add Dockerfile to the container as documentation
COPY Dockerfile /Dockerfile
RUN useradd --create-home --home-dir /home/apiuser apiuser \
        && chown -R apiuser:apiuser /home/apiuser

COPY docker/startapi.sh /home/apiuser/startapi.sh
COPY requirements.txt /home/apiuser/requirements.txt


# Add the API server and client.py
COPY main.py /home/apiuser/
COPY worker.py /home/apiuser/

WORKDIR /home/apiuser
RUN /usr/sbin/setup.sh

CMD ["bash", "/home/apiuser/startapi.sh"]
