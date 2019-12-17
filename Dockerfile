FROM ubuntu:xenial
MAINTAINER ryan@gruss.dev

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -qyy \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    python-dev python3-dev python-virtualenv python3-setuptools \
    python3-pip python3-lxml wget libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev \
    tcl8.6-dev tk8.6-dev python-tk chromium-browser unzip

RUN pip3 install --upgrade selenium pyyaml requests lxml Flask Jinja2 Werkzeug gunicorn pymongo piexif pillow pytz google-cloud-storage

RUN wget https://chromedriver.storage.googleapis.com/79.0.3945.36/chromedriver_linux64.zip
RUN unzip chromedriver_linux64.zip
RUN chmod +x chromedriver
RUN cp chromedriver /usr/local/bin/

WORKDIR /app
ADD "py/*" /app/
CMD ["python3.4", "/app/app.py"]
