#!/bin/bash -x
# echo "$PROJECT_TZ" > /etc/timezone

set -ev

echo "Europe/Amsterdam" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"
if ! grep -Fxq "deb http://ftp.debian.org/debian jessie-backports main" /etc/apt/sources.list; then
    echo "deb http://ftp.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
fi

# Install go 1.5
# wget -q https://storage.googleapis.com/golang/go1.5.3.linux-amd64.tar.gz -P /tmp/
# sudo tar -C /usr/local -xzf /tmp/go1.5.3.linux-amd64.tar.gz
wget https://storage.googleapis.com/golang/go1.5.linux-amd64.tar.gz /tmp/
tar -C /usr/local -xzf go1.5.linux-amd64.tar.gz


# According to certbot readme, this should be set:
# TODO: Check GOROOT path
if ! grep -Fxq "export GOROOT=/usr/local/go" ~/.bashrc; then
    echo "export GOROOT=/usr/local/go" >> ~/.bashrc
fi
if ! grep -Fxq "export GOPATH=/gopath" ~/.bashrc; then
    echo "export GOPATH=/gopath" >> ~/.bashrc
fi
if ! grep -Fxq "export PATH=\$GOROOT/bin:\$PATH" ~/.bashrc; then
  echo "export PATH=\$GOROOT/bin:\$PATH" >> ~/.bashrc
fi
if ! grep -Fxq "export PATH=\$PATH:\$GOPATH/bin" ~/.bashrc; then
    echo "export PATH=\$PATH:\$GOPATH/bin" >> ~/.bashrc
fi
if ! grep -Fxq "127.0.0.1 boulder boulder-rabbitmq boulder-mysql" /etc/hosts; then
  echo '127.0.0.1 boulder boulder-rabbitmq boulder-mysql' >> /etc/hosts
fi

source ~/.bashrc


apt-get update
apt-get upgrade -y
# TODO: Check libltdl version
apt-get install -y \
    sudo htop net-tools tcpdump ufw git curl \
    openssl ca-certificates \
    python2.7 python-setuptools python-virtualenv \
    rabbitmq-server make libltdl-dev mariadb-server nginx-light

apt-get install -y -t jessie-backports \
    protobuf-compiler libprotobuf-dev \
    python-protobuf protobuf-c-compiler 

echo boulder.local > /etc/hostname
hostname -F /etc/hostname

ufw allow ssh
ufw allow 4000
ufw allow 8000
ufw allow 8001
ufw allow 8002
ufw allow 8003
ufw allow 8004
ufw allow 8005
ufw default deny incoming
ufw --force enable

# Create new go directory for GOPATH
# Paths needed for installing go dependencies
mkdir -p /gopath/bin
mkdir -p /gopath/src



# cd /vagrant
# ./letsencrypt-auto-source/letsencrypt-auto --os-packages-only
# ./tools/venv.sh
# ./tests/boulder-start.sh

virtualenv /boulder_venv -p /usr/bin/python2
source /boulder_venv/bin/activate

if [ ! -d /boulder ]; then
    git clone https://github.com/letsencrypt/boulder.git /boulder
    cd /boulder
else
    cd /boulder
    git pull
fi

# TODO: Missing paths?
# mkdir /boulder/bin
# mkdir /boulder/src

# curl https://glide.sh/get | sh
# 
# glide create --non-interactive
# glide install

cd /boulder

go get -d github.com/letsencrypt/boulder/...
# go get \
#   bitbucket.org/liamstask/goose/cmd/goose \
#   github.com/golang/lint/golint \
#   github.com/golang/mock/mockgen \
#   github.com/golang/protobuf/proto \
#   github.com/golang/protobuf/protoc-gen-go \
#   github.com/jsha/listenbuddy \
#   github.com/kisielk/errcheck \
#   github.com/mattn/goveralls \
#   github.com/modocache/gover \
#   github.com/tools/godep \
#   golang.org/x/tools/cover \
#   github.com/letsencrypt/boulder/cmd \
#   github.com/streadway/amqp \
#   github.com/miekg/dns \
#   gopkg.in/gorp.v1 \
#   github.com/google/certificate-transparency/go \
#   github.com/letsencrypt/go-safe-browsing-api \
#   github.com/facebookgo/httpdown \
#   gopkg.in/yaml.v2 \
#   github.com/weppos/publicsuffix-go/publicsuffix \
#   github.com/google/certificate-transparency/go/client \
#   github.com/facebookgo/clock \
#   github.com/facebookgo/stats \
#   github.com/google/certificate-transparency/go/x509 \
#   github.com/google/certificate-transparency/go/asn1 \
#   github.com/google/certificate-transparency/go/x509/pkix

# TODO: this downloads /gopath/src/github.com/letsencrypt/go to a wrong
# directory. It works better when you checkout the master branch in that
# directory

export GO15VENDOREXPERIMENT=1

./test/setup.sh

# go run cmd/rabbitmq-setup/main.go -server amqp://boulder-rabbitmq

cat > "/lib/systemd/system/boulder.service" <<EOF
[Unit]
Description=Boulder Server
After=network.target
Wants=mariadb.service,rabbitmq.service
[Service]
Type=simple
KillMode=process
RemainAfterExit=no
Restart=always
ExecStart=/bin/bash -c "cd /boulder; /boulder_venv/bin/python /boulder/start.py"
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable boulder.service
systemctl start boulder.service

echo "Provisioning completed."
