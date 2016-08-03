#!/bin/bash -x
echo "$PROJECT_TZ" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"
echo "deb http://ftp.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
apt-get update
apt-get upgrade -y
apt-get install -y \
    sudo htop net-tools tcpdump ufw git haproxy \
    openssl ca-certificates \
    python python-setuptools python-dev libssl-dev
apt-get install -y -t jessie-backports certbot

easy_install pip
pip install virtualenv

ufw allow ssh
ufw allow http
ufw allow https
ufw default deny incoming
ufw --force enable

virtualenv "/${PROJECT_NAME}_venv" -p /usr/bin/python
source "/${PROJECT_NAME}_venv/bin/activate"
cd "/${PROJECT_NAME}"
pip install --editable .

echo "${PROJECT_CLIENT_HOSTNAME}" > /etc/hostname
hostname -F /etc/hostname

cat <<EOF >> /etc/letsencrypt/cli.ini
server http://le.wtf
EOF

cat <<EOF >> /etc/hosts
${PROJECT_SERVER_IP}   le.wtf
${PROJECT_SERVER_IP}   le1.wtf
${PROJECT_SERVER_IP}   le2.wtf
${PROJECT_SERVER_IP}   le3.wtf
${PROJECT_SERVER_IP}   nginx.wtf
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

cat <<EOF > /etc/systemd/system/letsencrypt.service
[Unit]
Description=Renew Let's Encrypt Certificates

[Service]
Type=simple
ExecStart=/usr/bin/certbot renew -q
EOF

systemctl enable letsencrypt.timer
systemctl start letsencrypt.timer

echo "Provisioning completed."
