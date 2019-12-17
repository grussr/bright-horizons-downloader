FROM ubuntu:xenial
MAINTAINER dashah@gmail.com

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -qyy \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    python-dev python3-dev python-virtualenv python3-setuptools \
    python3-pip firefox python3-lxml wget libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev \
    tcl8.6-dev tk8.6-dev python-tk chromium-browser

RUN pip3 install --upgrade selenium pyyaml requests Flask Jinja2 Werkzeug gunicorn pymongo piexif boto3 Pillow

#RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.20.0/geckodriver-v0.20.0-linux64.tar.gz
#RUN tar -xvzf geckodriver-v0.20.0-linux64.tar.gz
#RUN rm geckodriver-v0.20.0-linux64.tar.gz
#RUN chmod +x geckodriver
#RUN cp geckodriver /usr/local/bin/

WORKDIR /app
ADD "py/*" /app/
CMD ["python3.4", "/app/app.py"]
