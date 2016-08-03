#!/bin/bash -x
echo "$PROJECT_TZ" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"
echo "deb http://ftp.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
apt-get update
apt-get upgrade -y
apt-get install -y \
    sudo htop net-tools tcpdump ufw git haproxy tmux watch curl wget \
    openssl ca-certificates build-essential libffi-dev \
    python python-setuptools python-dev libssl-dev
apt-get install -y -t jessie-backports certbot

pip install --upgrade setuptools

easy_install pip
pip install virtualenv

ufw allow ssh
ufw allow http
ufw allow https
ufw default deny incoming
ufw --force enable

echo "${PROJECT_CLIENT_HOSTNAME}" > /etc/hostname
hostname -F /etc/hostname

virtualenv "/${PROJECT_NAME}_venv" -p /usr/bin/python
chown -R vagrant: "/${PROJECT_NAME}_venv/bin/activate"
source "/${PROJECT_NAME}_venv/bin/activate"
cd "/${PROJECT_NAME}"
pip install --editable .

cat <<EOF >> /etc/hosts
${PROJECT_SERVER_IP}   le.wtf
${PROJECT_SERVER_IP}   le1.wtf
${PROJECT_SERVER_IP}   le2.wtf
${PROJECT_SERVER_IP}   le3.wtf
${PROJECT_SERVER_IP}   nginx.wtf
EOF

mkdir -p "/${PROJECT_NAME}/working/logs"
mkdir -p "/${PROJECT_NAME}/working/config"
chown -R vagrant: "/${PROJECT_NAME}/working"
mkdir -p /home/vagrant/.config/letsencrypt
cat <<EOF >> /home/vagrant/.config/letsencrypt/cli.ini
work-dir=/${PROJECT_NAME}/working/
logs-dir=/${PROJECT_NAME}/working/logs/
config-dir=/${PROJECT_NAME}/working/config
agree-tos
no-self-upgrade
register-unsafely-without-email
text
domain example.org
configurator certbot-haproxy:haproxy
server http://le.wtf
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
EOF

#cat <<EOF > /etc/systemd/system/letsencrypt.timer
#[Unit]
#Description=Run Let's Encrypt every 12 hours
#
#[Timer]
## Time to wait after booting before we run first time
#OnBootSec=2min
## Time between running each consecutive time
#OnUnitActiveSec=12h
#Unit=letsencrypt.service
#
#[Install]
#WantedBy=timers.target
#EOF
#
#cat <<EOF > /etc/systemd/system/letsencrypt.service
#[Unit]
#Description=Renew Let's Encrypt Certificates
#
#[Service]
#Type=simple
#ExecStart=/usr/bin/certbot renew -q
#EOF
#
#systemctl enable letsencrypt.timer
#systemctl start letsencrypt.timer

echo "Provisioning completed."
