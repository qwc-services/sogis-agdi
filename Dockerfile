# WSGI service environment

FROM sourcepole/qwc-uwsgi-base:alpine-v2024.01.16

# Required for psychopg, --> https://github.com/psycopg/psycopg2/issues/684
RUN apk add --no-cache --update postgresql-dev gcc python3-dev musl-dev

# Workaround for "ImportError: cannot import name 'PackageFinder'"
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py pip

ADD . /srv/qwc_service
RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt
