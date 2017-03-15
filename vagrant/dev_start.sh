#!/bin/bash

CMDS="vagrant"
DEPS="vagrant"
VAGRANT_PLUGINS_REQUIRED=("vagrant-hostmanager" "vagrant-vbguest")

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
    sudo bash -c "$@"
}

if ! commands_exist "${CMDS}"; then
    log "Missing one or more dependencies."
    please_install "${DEPS}"
    exit 1
fi

log "Checking for vagrant plugins.."
INSTALLED=$(vagrant plugin list | awk '{print $1;}' | xargs)
for PLUGIN in "${VAGRANT_PLUGINS_REQUIRED[@]}"; do
    if [[ $INSTALLED != *$plugin* ]]; then
        log "Installing vagrant plugin \"${PLUGIN}\""
        vagrant plugin install "${PLUGIN}"
    fi
done

if ! grep -Fxq "192.168.33.222 testsite.nl" /etc/hosts; then
  do_sudo "echo '192.168.33.222 testsite.nl' >> /etc/hosts"
fi

log "Starting Boulder CA server instance.."
if vagrant up boulder; then
    log "Starting LE HAProxy client vm.."
    vagrant up lehaproxy
else
    log "ERROR: Couldn't start boulder server!"
    exit 1
fi

echo "You can now connect to the Vagrant instance:"
echo "vagrant ssh lehaproxy"
echo "After connecting please run:"
echo "cd /lehaproxy/; source /lehaproxy_venv/bin/activate"
echo "You can now run certbot with the HAProxy plugin installed:"
echo "certbot run"
