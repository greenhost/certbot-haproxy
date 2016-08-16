"""HAProxy plugin constants.

Operation system specific variables are saved in this module. Currently
includes:

    - server_root: the folder containing HAProxy files
    - restart_cmd: the command to restart haproxy (command is a list)
    - conftest_cmd: the command to test the haproxy configuration
    - haproxy_config: the path to the haproxy configuration file
    - crt_directory: the directory to which the crt frontend option points.
      This directory needs to be writeable by the user that runs certbot.

Defaults to the values for DEBIAN_JESSIE if no suitable operating system is
found.
"""
import re
from certbot import util

RE_HAPROXY_DOMAIN_ACL = re.compile(
    r'\s*acl (?P<name>[0-9a-z_\-.]+) '
    r'hdr\(host\) -i '
    r'(?P<domain>'  # Start group "domain"
    r'(?:[0-9-a-z](?:[a-z0-9-]{0,61}[a-z0-9]\.)+)'  # (sub-)domain parts
    r'(?:[0-9-a-z](?:[a-z0-9-]{0,61}[a-z0-9]))'  # TLD part
    r')'  # End group "domain"
)

CLI_DEFAULTS_DEBIAN_JESSIE = dict(
    service_manager='systemctl',
    version_cmd=['/usr/sbin/haproxy', '-v'],
    restart_cmd=['sudo', 'systemctl', 'restart', 'haproxy'],
    # Needs the config file as an argument:
    conftest_cmd=['/usr/sbin/haproxy', '-c', '-f'],
    haproxy_config='/etc/haproxy/haproxy.cfg',
    # Needs to be writeable by the user that will run certbot
    crt_directory='/etc/ssl/crt/',
)

CLI_DEFAULTS_DEBIAN_WHEEZY = dict(
    service_manager='service',
    version_cmd=['/usr/sbin/haproxy', '-v'],
    restart_cmd=['service', 'haproxy', 'restart'],
    # Needs the config file as an argument:
    conftest_cmd=['/usr/sbin/haproxy', '-c', '-f'],
    haproxy_config='/etc/haproxy/haproxy.cfg',
    # Needs to be writeable by the user that will run certbot
    crt_directory='/etc/ssl/crt/',
)

CLI_DEFAULTS = {
    "debian": CLI_DEFAULTS_DEBIAN_JESSIE,
    "debian:jessie": CLI_DEFAULTS_DEBIAN_JESSIE,
    "debian:wheezy": CLI_DEFAULTS_DEBIAN_WHEEZY,
    "ubuntu": CLI_DEFAULTS_DEBIAN_WHEEZY
}


def os_constant(key):
    """Get a constant value for operating system

    :param str key: name of cli constant
    :return: value of constant for active os
    """
    os_info = util.get_os_info()
    try:
        constants = CLI_DEFAULTS[os_info[0].lower()]
    except KeyError:
        constants = CLI_DEFAULTS["debian"]
    return constants[key]
