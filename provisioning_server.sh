#!/bin/bash -x
echo "$PROJECT_TZ" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"
echo "deb http://ftp.debian.org/debian jessie-backports main" >> /etc/apt/sources.list
apt-get update
apt-get upgrade -y
apt-get install -y \
    sudo htop net-tools tcpdump ufw git curl \
    openssl ca-certificates golang \
    python2.7 python-setuptools python-virtualenv \
    rabbitmq-server make libltdl-dev mariadb-server nginx-light

apt-get install -y -t jessie-backports \
    protobuf-compiler golang-goprotobuf-dev libprotobuf-dev \
    python-protobuf protobuf-c-compiler golang-protobuf-extensions-dev

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

if ! grep -Fxq "export GOROOT=/usr/local/go" ~/.bashrc; then
    echo "export GOROOT=/usr/local/go" >> ~/.bashrc
fi
if ! grep -Fxq "export GOPATH=/boulder" /root/.bashrc; then
    echo "export GOPATH=/boulder" >> /root/.bashrc
fi
if ! grep -Fxq "export PATH=\$GOROOT/bin:\$PATH" ~/.bashrc; then
  echo "export PATH=\$GOROOT/bin:\$PATH" >> ~/.bashrc
fi
if ! grep -Fxq "export PATH=\$PATH:\$GOPATH" /root/.bashrc; then
    echo "export PATH=\$PATH:\$GOPATH" >> /root/.bashrc
fi
if ! grep -Fxq "127.0.0.1 boulder boulder-rabbitmq boulder-mysql" /etc/hosts; then
  echo '127.0.0.1 boulder boulder-rabbitmq boulder-mysql' >> /etc/hosts
fi

source ~/.bashrc

# wget -q https://storage.googleapis.com/golang/go1.5.3.linux-amd64.tar.gz -P /tmp/
# sudo tar -C /usr/local -xzf /tmp/go1.5.3.linux-amd64.tar.gz
# if ! grep -Fxq "export GOROOT=/usr/local/go" ~/.profile ; then echo "export GOROOT=/usr/local/go" >> ~/.profile; fi
# if ! grep -Fxq "export PATH=\\$GOROOT/bin:\\$PATH" ~/.profile ; then echo "export PATH=\\$GOROOT/bin:\\$PATH" >> ~/.profile; fi

cd /vagrant
./letsencrypt-auto-source/letsencrypt-auto --os-packages-only
./tools/venv.sh
./tests/boulder-start.sh

virtualenv /boulder_venv -p /usr/bin/python2
source /boulder_venv/bin/activate

git clone https://github.com/letsencrypt/boulder.git /boulder
cd /boulder
mkdir /boulder/bin
mkdir /boulder/src

curl https://glide.sh/get | sh

glide create --non-interactive
glide install

#go get \
#  bitbucket.org/liamstask/goose/cmd/goose \
#  github.com/golang/lint/golint \
#  github.com/golang/mock/mockgen \
#  github.com/golang/protobuf/proto \
#  github.com/golang/protobuf/protoc-gen-go \
#  github.com/jsha/listenbuddy \
#  github.com/kisielk/errcheck \
#  github.com/mattn/goveralls \
#  github.com/modocache/gover \
#  github.com/tools/godep \
#  golang.org/x/tools/cover \
#  github.com/letsencrypt/boulder/cmd \
#  github.com/streadway/amqp

./test/create_db.sh
go run cmd/rabbitmq-setup/main.go -server amqp://boulder-rabbitmq

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
ExecStart=/boulder_venv/bin/python /boulder/start.py"
[Install]
WantedBy=multi-user.target
EOF

systemctl enable boulder.service
systemctl start boulder.service
echo "Provisioning completed."
