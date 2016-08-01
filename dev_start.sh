#!/bin/bash

CMDS="vagrant"
DEPS="vagrant"

VERBOSE=0
for arg in "$@"; do
    if [ "${arg}" = "-v" -o "${arg}" = "--verbose" ]; then
        VERBOSE=1
        echo "Verbose mode enabled"
    fi
done

commands_exist () {
    DEPS_MISSING=0
    for cmd in $1; do
        if ! type "${cmd}" &> /dev/null; then
            DEPS_MISSING=1
            echo "Dependency '${cmd}' is not installed."
        fi
    done
    return $DEPS_MISSING
}

function_defined() {
    type "$1" &> /dev/null;
}

please_install () {
    if [ -f /etc/redhat-release ] ; then
        PKMGR=$(which yum)
    elif [ -f /etc/debian_version ] ; then
        PKMGR=$(which apt-get)
    fi
    echo
    echo "Before running this script, please run:"
    echo "${PKMGR} install $1"
}

log () {
    if [ $VERBOSE -eq 1 ]; then
        echo "$1"
    fi
}

SUDO=0
do_sudo () {
    if [ $SUDO -eq 0 ]; then
        echo "Your hosts file does not contain the required entries, will need"
        echo "root privileges to set them.."
        sudo ls &> /dev/null
        SUDO=1
    fi
}

if ! commands_exist "${CMDS}"; then
    log "Missing one or more dependencies."
    please_install "${DEPS}"
    exit 1
fi

#log "Checking for vagrant plugins.."
#vagrant plugin install vagrant-hostmanager
#vagrant plugin install vagrant-vbguest

log "Checking hosts file for required entries.."
for hostname in "le.wtf le1.wtf le2.wtf le3.wtf nginx.wtf"; do
    if ! grep "${hostname}" /etc/hosts &> /dev/null; then
        do_sudo
        sudo cat <<EOF >> /etc/hosts
            127.0.0.1   ${hostname}
EOF
    fi
done

if ! grep "lehaproxy.local" /etc/hosts &> /dev/null; then
        do_sudo
        sudo cat <<EOF >> /etc/hosts
            127.0.0.1   lehaproxy.lan
EOF
fi
if ! grep "boulder.local" /etc/hosts &> /dev/null; then
        do_sudo
        sudo cat <<EOF >> /etc/hosts
            127.0.0.1   boulder.lan
EOF
fi
log "Starting LE HAProxy client and server instance.."
vagrant up

echo "You can now connect to the Vagrant instance:"
echo "vagrant ssh lehaproxy"
echo "After connecting please run:"
echo "sudo -s; cd /lehaproxy/; source /lehaproxy_venv/"


