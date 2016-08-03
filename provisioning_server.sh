#!/bin/bash -x
set -ev
echo "$PROJECT_TZ" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
export DEBIAN_FRONTEND="noninteractive"

# Install go 1.5
wget -q https://storage.googleapis.com/golang/go1.5.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.5.linux-amd64.tar.gz

# Set GOROOT and GOPATH so that GO knows where it is and where it can install
# deps
if ! grep -Fxq "export GOROOT=/usr/local/go" ~/.variables; then
    echo "export GOROOT=/usr/local/go" >> ~/.variables
fi
if ! grep -Fxq "export GOPATH=/gopath" ~/.variables; then
    echo "export GOPATH=/gopath" >> ~/.variables
fi
if ! grep -Fxq "export PATH=\$GOROOT/bin:\$PATH" ~/.variables; then
    echo "export PATH=\$GOROOT/bin:\$PATH" >> ~/.variables
fi
if ! grep -Fxq "export GO15VENDOREXPERIMENT=1" ~/.variables; then
    echo "export GO15VENDOREXPERIMENT=1" >> ~/.variables
fi
# Add go to PATH variable
if ! grep -Fxq "export PATH=\$PATH:\$GOPATH/bin:usr/local/go/bin" ~/.variables; then
    echo "export PATH=\$PATH:\$GOPATH/bin:usr/local/go/bin" >> ~/.variables
fi

if ! grep -Fxq "source ~/.variables" ~/.bashrc; then
    echo "source ~/.variables" >> ~/.bashrc
fi
if ! grep -Fxq "127.0.0.1 boulder boulder-rabbitmq boulder-mysql" /etc/hosts; then
  echo '127.0.0.1 boulder boulder-rabbitmq boulder-mysql' >> /etc/hosts
fi

source ~/.variables

# Add PPA for MariaDb
sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
sudo add-apt-repository 'deb [arch=amd64,i386,ppc64el] http://mirrors.supportex.net/mariadb/repo/10.1/ubuntu trusty main'

apt-get update
apt-get upgrade -y

apt-get install -y \
    sudo htop net-tools tcpdump ufw git curl g++ \
    openssl ca-certificates \
    python2.7 python-setuptools python-virtualenv \
    rabbitmq-server make libltdl-dev mariadb-server nginx-light \
    softhsm libsofthsm-dev

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

virtualenv /boulder_venv -p /usr/bin/python2
source /boulder_venv/bin/activate


# Install godep
go get github.com/tools/godep

# Goose is needed by the setup script (hope this will be fixed soon)
go get bitbucket.org/liamstask/goose/cmd/goose

# Install boulder into the gopath
go get -d github.com/letsencrypt/boulder/...

# Enter the boulder directory
cd /gopath/src/github.com/letsencrypt/boulder

# Install alle dependencies
godep restore

# Remaining setup
./test/setup.sh

# Apply softhsm configuration
./test/make-softhsm.sh

# Add softhsm configuration to .variables
if ! grep -Fxq "export SOFTHSM_CONF=$PWD/test/softhsm.conf" ~/.variables; then
    echo "export SOFTHSM_CONF=$PWD/test/softhsm.conf" >> ~/.variables
fi

# Change pkcs to softhsm
if grep -Fq "/usr/local/lib/libpkcs11-proxy.so" test/test-ca.key-pkcs11.json; then
    git apply /vagrant/softhsm.patch
fi

echo "Provisioning completed."
