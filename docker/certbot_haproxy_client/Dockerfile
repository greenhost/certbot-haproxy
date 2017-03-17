FROM certbot:certbot
MAINTAINER Maarten <maarten@greenhost.nl>
MAINTAINER Chris <chris@greenhost.nl>

EXPOSE 443

WORKDIR /opt/certbot-haproxy

RUN apk add --no-cache --virtual .certbot-deps haproxy
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        linux-headers \
        openssl-dev \
        musl-dev \
        libffi-dev \
    && pip install --no-cache-dir --editable /opt/certbot-haproxy \
    && apk del .build-deps

# TODO: Maybe there is no certbot user yet?
RUN echo "%certbot ALL=NOPASSWD: /bin/systemctl restart haproxy" >> /etc/sudoers

ADD ./certbot_haproxy_client/cli.ini /etc/letsencrypt/cli.ini
ADD ./certbot_haproxy_client/haproxy.cfg /etc/haproxy/haproxy.cfg

RUN mkdir -p /opt/certbot/haproxy_fullchains
