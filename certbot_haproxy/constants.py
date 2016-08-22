"""HAProxy plugin constants.

Operation system specific constants are saved in this module as dictionaries,
e.g.: `CLI_DEFAULTS_DEBIAN_JESSIE`. Currently these are defined for:

  - Debian Jessie (8)
  - Debian Wheezy (7)
  - Ubuntu Trusty (14.04)
  - Ubuntu Utopic (14.10)
  - Ubuntu Vivid (15.04)
  - Ubuntu Wily (15.10)
  - Ubuntu Xenial (16.04)

You can define new lists below following the instructions hereafter, please
consider making a pull-request when you do so, so others may benefit of your
work too.

    .. attribute:: CLI_DEFAULTS_OS_NAME['service_manager']

        A string containing the name of the servicemanager executable of the
        OS, e.g.: `systemctl` (systemd) on Debian >= 8 and Ubuntu >=
        16.04; `service` on Debian Wheezy and Ubuntu =< 14.04.

    .. attribute:: CLI_DEFAULTS_OS_NAME['restart_cmd']

        The command to restart HAProxy, this is defined as a sequence of
        commands and arguments, this is done so commands and arguments can be
        safely escaped, read more about this `here`_.

        .. _here: https://docs.python.org/2/library/subprocess.html

    .. attribute:: CLI_DEFAULTS_OS_NAME['conftest_cmd']

        The command to test the HAProxy configuration, this is most likely
        `haproxy -c -f [path_to_configuration]` for HAProxy. This
        command should return exit code `0` if the configuration is correct
        and non-`0` if there were configuration errors.

    .. attribute:: CLI_DEFAULTS_OS_NAME['haproxy_config']

        The path to the HAProxy configuration file.

    .. attribute:: CLI_DEFAULTS_OS_NAME['crt_directory']

        The directory in which HAProxy is configured to search for SSL
        certificates.

        .. note:: This directory needs to be writeable by the user that runs
            certbot.
"""

import logging
import re
from distutils.version import LooseVersion
from certbot import util
from certbot import errors
from certbot_haproxy.util import MemoiseNoArgs

RE_HAPROXY_DOMAIN_ACL = re.compile(
    r'\s*acl (?P<name>[0-9a-z_\-.]+) '
    r'hdr\(host\) -i '
    r'(?P<domain>'  # Start group "domain"
    r'(?:[0-9-a-z](?:[a-z0-9-]{0,61}[a-z0-9]\.)+)'  # (sub-)domain parts
    r'(?:[0-9-a-z](?:[a-z0-9-]{0,61}[a-z0-9]))'  # TLD part
    r')'  # End group "domain"
)

CLI_DEFAULTS_DEBIAN_BASED_SYSTEMD_OS = dict(
    service_manager='systemctl',
    version_cmd=['/usr/sbin/haproxy', '-v'],
    restart_cmd=['sudo', 'systemctl', 'restart', 'haproxy'],
    # Needs the config file as an argument:
    conftest_cmd=['/usr/sbin/haproxy', '-c', '-f'],
    haproxy_config='/etc/haproxy/haproxy.cfg',
    # Needs to be writeable by the user that will run certbot
    crt_directory='/opt/cerbot/haproxy_fullchains',
)

CLI_DEFAULTS_DEBIAN_BASED_PRE_SYSTEMD_OS = dict(
    service_manager='service',
    version_cmd=['/usr/sbin/haproxy', '-v'],
    restart_cmd=['service', 'haproxy', 'restart'],
    # Needs the config file as an argument:
    conftest_cmd=['/usr/sbin/haproxy', '-c', '-f'],
    haproxy_config='/etc/haproxy/haproxy.cfg',
    # Needs to be writeable by the user that will run certbot
    crt_directory='/opt/cerbot/haproxy_fullchains',
)

CLI_DEFAULTS = {
    "debian": {
        '_min_version': '7',
        '_max_version': '8',
        '7': CLI_DEFAULTS_DEBIAN_BASED_PRE_SYSTEMD_OS,
        '8': CLI_DEFAULTS_DEBIAN_BASED_SYSTEMD_OS
    },
    "ubuntu": {
        '_min_version': '14.04',
        '_max_version': '16.04',
        '14.04': CLI_DEFAULTS_DEBIAN_BASED_PRE_SYSTEMD_OS,
        '14.10': CLI_DEFAULTS_DEBIAN_BASED_PRE_SYSTEMD_OS,
        '15.04': CLI_DEFAULTS_DEBIAN_BASED_SYSTEMD_OS,
        '15.10': CLI_DEFAULTS_DEBIAN_BASED_SYSTEMD_OS,
        '16.04': CLI_DEFAULTS_DEBIAN_BASED_SYSTEMD_OS
    }
}

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@MemoiseNoArgs  # Cache the return value
def os_analyse():
    """
        Returns tuple containing the OS distro and version corresponding with
        supported versions and caches the result. Output is cached.

        :returns: (distro, version_nr)
        :rtype: tuple
    """
    os_info = util.get_os_info()
    distro = os_info[0].lower()
    version = os_info[1]
    if distro not in CLI_DEFAULTS:
        raise errors.NotSupportedError(
            "We're sorry, your OS  %s %s is currently not supported :("
            " you may be able to get this plugin working by defining a list of"
            " CLI_DEFAULTS in our `constants` module. Please consider making "
            " a pull-request if you do!"
        )

    if version not in CLI_DEFAULTS[distro]:
        min_version = CLI_DEFAULTS[distro]['_min_version']
        max_version = CLI_DEFAULTS[distro]['_max_version']
        if LooseVersion(version) < LooseVersion(min_version):
            raise errors.NotSupportedError(
                "The OS you are using (%s %s) is not supported by this"
                " plugin, minimum supported version is %s %s",
                distro, version, distro, version
            )
        elif LooseVersion(version) > LooseVersion(max_version):
            logger.warn(
                "Your OS version \"%s %s\" is not officially supported by"
                " this plugin yet. Will try to run with the most recent"
                " set of constants (%s %s), your mileage may vary.",
                distro, version, distro, max_version
            )
            version = max_version
        else:
            # Version within range but not occurring in CLI_DEFAULTS
            versions = CLI_DEFAULTS[distro]
            # Only items whose contents stripped of "." are digits, e.g.: 16.04
            versions = [v for v in versions if v.replace(".", "").isdigit()]
            compare = LooseVersion(version)
            for index, versionno in enumerate(sorted(versions)):
                # Find the highest supported version number _under_ the
                # detected version number. In other words: the detected version
                # number should be smaller than next one in the loop, but
                # bigger than the current one.

                # Next version number is?
                peek = versions[index+1]

                if LooseVersion(peek) > compare > LooseVersion(versionno):
                    logger.warn(
                        "Your OS version \"%s %s\" is not officially supported"
                        " by this plugin yet. Will try to run with the most"
                        " recent set of constants of a version before your"
                        " os's (%s %s), your mileage may vary.",
                        distro, version, distro, versionno
                    )
                    version = versionno
                    break

    return (distro, version)


def os_constant(key):
    """Get a constant value for operating system

    :param str key: name of cli constant
    :return: value of constant for active os
    """
    distro, version = os_analyse()
    return CLI_DEFAULTS[distro][version][key]
