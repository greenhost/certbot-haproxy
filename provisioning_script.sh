#!/bin/bash -x
echo "deb http://ftp.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
apt-get update
apt-get upgrade -y
apt-get install -y \
    sudo htop net-tools tcpdump ufw git haproxy\
    openssl ca-certificates \
    python python-setuptools virtualenv
apt-get install -y -t jessie-backports certbot

ufw allow ssh
ufw allow http
ufw allow https
ufw default deny incoming

# echo HOSTNAME > /etc/hostname
# hostname -F /etc/hostname

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
Description=Renew Let's Encrypt Certificate

[Service]
Type=simple
ExecStart=certbot renew q
EOF

systemctl start letsencrypt.timer
systemctl enable letsencrypt.timer
