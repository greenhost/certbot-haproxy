FROM certbot/certbot:v0.11.0
MAINTAINER Maarten <maarten@greenhost.nl>
MAINTAINER Chris <chris@greenhost.nl>

EXPOSE 443

WORKDIR /opt/certbot-haproxy

RUN apk add --no-cache haproxy openrc

RUN apk add --no-cache --virtual .build-deps \
        gcc \
        linux-headers \
        openssl-dev \
        musl-dev \
        libffi-dev

# Copy in the certbot-haproxy sources
COPY . .

RUN pip install --no-cache-dir --editable /opt/certbot-haproxy

# RUN apk del .build-deps

# TODO: Maybe there is no certbot user yet?
RUN echo "%certbot ALL=NOPASSWD: /bin/systemctl restart haproxy" >> /etc/sudoers

ADD docker/certbot_haproxy_client/cli.ini /etc/letsencrypt/cli.ini
ADD docker/certbot_haproxy_client/haproxy.cfg /etc/haproxy/haproxy.cfg

RUN mkdir -p /opt/certbot/haproxy_fullchains
