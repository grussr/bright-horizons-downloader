FROM ubuntu:trusty
MAINTAINER dashah@gmail.com

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -qyy \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    python-virtualenv python3.4-dev python3-setuptools \
    python3-pip firefox python3-lxml wget

RUN pip3 install selenium pyyaml requests 
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.20.0/geckodriver-v0.20.0-linux64.tar.gz
RUN tar -xvzf geckodriver-v0.20.0-linux64.tar.gz
RUN rm geckodriver-v0.20.0-linux64.tar.gz
RUN chmod +x geckodriver
RUN cp geckodriver /usr/local/bin/

WORKDIR /app
ADD "py/*" /app/
CMD ["python3.4", "/app/app.py"]
