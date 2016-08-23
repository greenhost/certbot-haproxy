#!/bin/bash -x
echo "$PROJECT_TZ" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"
echo "deb http://ftp.debian.org/debian jessie-backports main" >> \
        /etc/apt/sources.list.d/jessie-backports.list
apt-get update
apt-get upgrade -y
apt-get install -y \
    sudo htop net-tools tcpdump ufw git haproxy tmux watch curl wget \
    openssl ca-certificates build-essential libffi-dev \
    python python-setuptools python-dev libssl-dev apache2

apt-get install -y -t jessie-backports certbot

easy_install pip
pip install --upgrade setuptools

pip install virtualenv

ufw allow ssh
ufw allow http
ufw allow https
ufw allow 8080
ufw default deny incoming
ufw --force enable

echo "${PROJECT_CLIENT_HOSTNAME}" > /etc/hostname
hostname -F /etc/hostname

virtualenv "/${PROJECT_NAME}_venv" -p /usr/bin/python
chown -R vagrant: "/${PROJECT_NAME}_venv/"
source "/${PROJECT_NAME}_venv/bin/activate"
cd "/${PROJECT_NAME}"
pip install --editable .

cat <<EOF >> /etc/hosts
${PROJECT_CLIENT_IP}   le.wtf
${PROJECT_CLIENT_IP}   le1.wtf
${PROJECT_CLIENT_IP}   le2.wtf
${PROJECT_CLIENT_IP}   le3.wtf
${PROJECT_CLIENT_IP}   testsite.nl
EOF

mkdir -p "/${PROJECT_NAME}/working/logs"
mkdir -p "/${PROJECT_NAME}/working/config"
chown -R vagrant: "/${PROJECT_NAME}/working"
mkdir -p /home/vagrant/.config/letsencrypt
# TODO: Maybe change greenhost.nl to something that is not example.org and yet
# does work.
cat <<EOF > /home/vagrant/.config/letsencrypt/cli.ini
work-dir=/${PROJECT_NAME}/working/
logs-dir=/${PROJECT_NAME}/working/logs/
config-dir=/${PROJECT_NAME}/working/config
agree-tos = True
no-self-upgrade = True
register-unsafely-without-email = True
text = True
debug = True
verbose = True
authenticator certbot-haproxy:haproxy-authenticator
installer certbot-haproxy:haproxy-installer
server http://le.wtf/directory
EOF
chown -R vagrant: /home/vagrant/.config/letsencrypt

cat <<EOF >> /root/.bashrc
alias ll='ls -l'
alias la='ls -A'
alias l='ls -CF'
EOF

cat <<EOF >> /home/vagrant/.bashrc
alias ll='ls -l'
alias la='ls -A'
alias l='ls -CF'
source /lehaproxy_venv/bin/activate
EOF

# Allow haproxy to read the dirs of the le plugin
# TODO: Does this even work with the `chroot` directive?
usermod -a -G vagrant haproxy

mkdir -p /opt/certbot/haproxy_fullchains
chown -R vagrant: /opt/certbot/

cat <<EOF > /etc/haproxy/haproxy.cfg
global
    log /dev/log    local0
    log /dev/log    local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

    # Default ciphers to use on SSL-enabled listening sockets.
    # Cipher suites chosen by following logic:
    #  - Bits of security 128>256 (weighing performance vs added security)
    #  - Key exchange: EECDH>DHE (faster first)
    #  - Mode: GCM>CBC (streaming cipher over block cipher)
    #  - Ephemeral: All use ephemeral key exchanges
    #  - Explicitly disable weak ciphers and SSLv3
    ssl-default-bind-ciphers AES128+AESGCM+EECDH:AES128+EECDH:AES128+AESGCM+DHE:AES128+EDH:AES256+AESGCM+EECDH:AES256+EECDH:AES256+AESGCM+EDH:AES256+EDH:!SHA:!MD5:!RC4:!DES:!DSS
    ssl-default-bind-options no-sslv3

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

frontend http-in
    # Listen on port 80
    bind *:80
    mode http
    # Listen on port 443
    # Uncomment after running certbot for the first time, a certificate
    # needs to be installed *before* HAProxy will be able to start when this
    # directive is not commented.
    #
    ## bind *:443 ssl crt /opt/certbot/haproxy_fullchains

    # Forward Cerbot verification requests to the certbot-haproxy plugin
    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot

    backend certbot
        log global
        mode http
        server certbot 127.0.0.1:8000

    # If redirection from port 80 to 443 is to be forced, uncomment the next
    # line. Keep in mind that the bind *:443 line should be uncommented and a
    # certificate should be present for all domains
    # redirect scheme https if !{ ssl_fc }

    # You can also configure separate domains to force a redirect from port 80
    # to 443 like this:
    # redirect scheme https if !{ ssl_fc } and [PUT YOUR DOMAIN NAME HERE]

    # The default backend is a cluster of 4 Apache servers that you need to
    # host.
    default_backend nodes

    backend nodes
        log global
        mode http
        option tcplog
        balance roundrobin
        option forwardfor
        option http-server-close
        option httpclose
        http-request set-header X-Forwarded-Port %[dst_port]
        http-request add-header X-Forwarded-Proto https if { ssl_fc }
        option httpchk HEAD / HTTP/1.1\r\nHost:localhost
        server node1 127.0.0.1:8080 check
        server node2 127.0.0.1:8080 check
        server node3 127.0.0.1:8080 check
        server node4 127.0.0.1:8080 check
EOF

cat <<EOF > /etc/apache2/sites-enabled/000-default.conf
<VirtualHost testsite.nl:8080>
        ServerName testsite.nl

        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html

        LogLevel error

        ErrorLog \${APACHE_LOG_DIR}/error.log
        CustomLog \${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
EOF

cat <<EOF > /etc/apache2/ports.conf
Listen 8080
EOF

# Insert a line into the sudoers file that makes our user able to restart
# haproxy (which it needs to do after every certificate edit)
bash -c 'echo "vagrant ALL=NOPASSWD: /bin/systemctl restart haproxy"
    | (EDITOR="tee -a" visudo)'


systemctl restart apache2
systemctl restart haproxy

# Scripts that run certificate renewal for all certificates every 12 hours. Only
# certificates that are due are renewed.
cat <<EOF > /etc/systemd/system/letsencrypt.service
[Unit]
Description=Renew Let's Encrypt Certificates

[Service]
Type=simple
User=vagrant
ExecStart=/usr/bin/certbot renew -q
EOF

cat <<EOF > /etc/systemd/system/letsencrypt.timer
[Unit]
Description=Run Let's Encrypt every 12 hours

[Timer]
# Time to wait after booting before we run first time
OnBootSec=2min
# Time between running each consecutive time
OnUnitActiveSec=12h
Unit=letsencrypt.service

[Install]
WantedBy=timers.target
EOF

# Reload for when there were already other scripts in place.
systemctl daemon-reload
# Enable and start the timer, which runs the service.
systemctl enable letsencrypt.timer
systemctl start letsencrypt.timer

echo "Provisioning completed."
