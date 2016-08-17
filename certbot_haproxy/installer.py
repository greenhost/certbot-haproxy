"""
    HAProxy Installer
    =================

    This installer combines the certificate files into one file and places them
    in the specified directory so HAProxy can use them. The directory can be
    specified in `.certbot_haproxy.constants` and has to be configured with
    HAProxy using the crt option for the bind directive::

        frontend http-in
            bind *:80
            mode http
            bind *:443 ssl crt /etc/ssl/crt/

    .. note:: You need to install one (default) certificate into this
        directory, otherwise HAProxy will not be able to start.

    .. note:: You need at least version 1.5 of HAProxy with OpenSSL built in.

    HAProxy is restarted by the installer with the restart_cmd from the
    `.certbot_haproxy.constants`. If you do not want to run lehaproxy as root
    (this is recommended), add this line to your sudoers file::

        $USER ALL=NOPASSWD: /bin/systemctl restart haproxy

    Be sure to replace `$USER` with the user that will be running the lehaproxy
    installer.
"""
import logging
import os
import glob
import subprocess
import re
from OpenSSL import crypto
from distutils.version import StrictVersion

import zope.component
import zope.interface

from certbot import interfaces

from certbot import errors
from certbot import util
from certbot import reverter
from certbot.plugins import common
from certbot_haproxy import constants

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name

HAPROXY_MIN_VERSION = "1.5"


@zope.interface.implementer(interfaces.IInstaller)
@zope.interface.provider(interfaces.IPluginFactory)
class HAProxyInstaller(common.Plugin):
    """HAProxy Installer."""

    description = "Certbot certificate installer for HAProxy."

    def __init__(self, *args, **kwargs):
        super(HAProxyInstaller, self).__init__(*args, **kwargs)

        #: This dictionary holds the file contents of all the changed
        #: certificates for HAProxy
        self.crt_files = {}
        #: This dictionary holds the file contents of all the new certificates
        #: for HAProxy
        self.new_crt_files = {}

        #: Notes to be added to each reverter checkpoint
        self.save_notes = ""

        #: File extension for saved certificates
        self.crt_postfix = ".pem"

        # Set up reverter
        self.reverter = reverter.Reverter(self.config)
        self.reverter.recovery_routine()

        #: Dict of supported enhancement functions:
        self._enhance_func = {}

    @classmethod
    def add_parser_arguments(cls, add):
        """
            This method adds extra CLI arguments to the plugin.
            The arguments can be retrieved by asking for corresponding names
            in `self.conf([argument name])`

            .. note:: This is an override a method defined in the parent, we
                are deliberately not calling super() because it would add
                arguments that we don't support.
        """
        add(
            "haproxy-crt-dir",
            help=(
                "Override the default certificate directory that will be"
                " configures in HAProxy. Default for this OS is \"{}\"".format(
                    constants.os_constant('crt_directory')
                )
            ),
            type=str,
            default=constants.os_constant('crt_directory')
        )
        add(
            "haproxy-config",
            help=(
                "Override the default haproxy configuration file location."
                " Default for this OS is \"{}\"".format(
                    constants.os_constant('haproxy_config')
                )
            ),
            type=str,
            default=constants.os_constant('haproxy_config')
        )
        add(
            "haproxy-ca-common-name",
            help=(
                "The name provided by the letsencrypt CA as its common name."
                " This is used to ensure that get_all_certs_keys() only"
                " returns letsencrypt certificates. Defaults to the value"
                " 'h2ppy h2cker fake CA' that is used by the local boulder."
            ),
            type=unicode,
            default=u'h2ppy h2cker fake CA'
        )

    @staticmethod
    def more_info():
        """
            This info string only appears in the curses UI in the plugin
            selection sequence.

            :returns: More information about this module.
            :rtype: str
        """
        return (
            "This installer combines the certificate files into one file and"
            " places them in the specified directory so HAProxy can use them."
        )

    def get_all_names(self):
        """
            Returns all names that are eligible for a SSL certificate.

            The certbot Installer plugin interface defines a function that
            should be implemented called
            `certbot.interfaces.get_all_names()` which finds domain names for
            which the plugin can request a certificate. By default this
            function implements this function by scanning the HAProxy
            configuration file for ACL rules that are formatted like this::

                acl [arbitrary_name] hdr(host) -i [domainname.tld]

            This is done by applying a regular expression to every line in the
            configuration file that contains `acl`, optionally prefixed by
            white space characters. You can change the regular expression if
            you are using a different pattern. The constant's name is
            `RE_HAPROXY_DOMAIN_ACL` which can be found in
            `.certbot_haproxy.constants`.

        :returns: Domain names in ACL rules in the HAProxy configuration file.
        :rtype: set
        """
        all_names = set()
        with open(self.conf('haproxy_config'), 'r') as config:
            for line in config:
                # Fast check for acl content..
                if 'acl' in line:
                    logger.info(line)
                    matches = constants.RE_HAPROXY_DOMAIN_ACL.match(line)
                    if matches is None:
                        continue
                    else:
                        name = matches.group('name')
                        domain = matches.group('domain')
                        logger.info(
                            "Found configuration \"%s\" for domain: \"%s\"",
                            name,
                            domain
                        )
                        all_names.add(domain)
        return all_names

    def view_config_changes(self):
        """Show all of the configuration changes that have taken place.

        :raises .errors.PluginError: If there is a problem while processing
            the checkpoints directories.

        """
        try:
            self.reverter.view_config_changes()
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

    @staticmethod
    def prepare():
        """Check if we can restart HAProxy when we are done.

        :raises .errors.NoInstallationError when no haproxy executable can
            be found
        :raises .errors.NoInstallationError when the default service manager
            executable can't be found
        :raises .errors.NotSupportedError when the installed haproxy version is
            incompatible with this plugin
        """
        service_mgr = constants.os_constant("service_manager")
        if not util.exe_exists(service_mgr):
            raise errors.NoInstallationError(
                "Can't find the default service manager for your system:"
                "{0}, please install it first or configure different OS"
                " constants".format(
                    service_mgr
                )
            )

        # Check that a supported version of HAProxy is installed.
        version_cmd = constants.os_constant("version_cmd")
        output = subprocess.check_output(version_cmd)
        matches = re.match(
            r'HA-Proxy version'
            r' (?P<version>[0-9]{1,4}\.[0-9]{1,4}\.[0-9a-z]{1,10}).*',
            output
        )
        if matches is None:
            raise errors.NoInstallationError(
                "It looks like HAProxy is not installed or the version might"
                " be incompatible."
            )
        else:
            version = matches.group('version')
            if StrictVersion(version) < StrictVersion(HAPROXY_MIN_VERSION):
                raise errors.NotSupportedError(
                    "Version {} of HAProxy is not supported by this plugin,"
                    " you need to install {} or higher to be"
                    " incompatible.".format(version, HAPROXY_MIN_VERSION)
                )

    def recovery_routine(self):
        """Revert all previously modified files.

        Reverts all modified files that have not been saved as a checkpoint

        :raises .errors.PluginError: If unable to recover the configuration

        """
        try:
            self.reverter.recovery_routine()
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

    def deploy_cert(self, domain,  # pylint: disable=too-many-arguments
                    cert_path, key_path, chain_path=None, fullchain_path=None):
        """Deploys the certificate to the HAProxy crt folder

        .. note:: This doesn't save the files!

        HAProxy needs the certificates and private key to be in one file. The
        private key in key_path is combined with the fullchain path if one is
        provided.  If no fullchain path is provided, the cert_path and the
        chain_path are used to create a similar document.

        These files are added to an internal dictionary. If the domain in
        ``domain`` already has a file in the ``crt_directory`` from
        `.certbot_haproxy.constants` it is added to self.crt_files, otherwise
        it is added to self.new_crt_files. These files are saved by the `.save`
        function.

        :param str domain: domain to deploy certificate file
        :param str cert_path: absolute path to the certificate file
        :param str key_path: absolute path to the private key file
        :param str chain_path: absolute path to the certificate chain file
        :param str fullchain_path: absolute path to the certificate fullchain
            file (cert plus chain)

        :raises errors.PluginError: When unable to deploy certificate due to
            a lack of information
        """
        crt_filename = constants.os_constant("crt_directory") + domain + \
            self.crt_postfix

        if not key_path:
            raise errors.PluginError(
                "The haproxy plugin requires --key-path to"
                " install a cert.")

        # Choose whether to make a new file or change an existing file
        if os.path.isfile(crt_filename):
            dic = self.crt_files
            self.save_notes += "Changed"
        else:
            self.save_notes += "Added"
            dic = self.new_crt_files
        self.save_notes += " certificate for domain %s\n" % domain

        if fullchain_path:
            with open(fullchain_path) as fullchain:
                self.save_notes += "\t- Used fullchain path %s\n" % \
                    fullchain_path
                dic[crt_filename] = fullchain.read()
        elif cert_path:
            with open(cert_path) as cert:
                self.save_notes += "\t- Used cert path %s\n" % cert_path
                dic[crt_filename] = cert.read()
            if chain_path:
                with open(chain_path) as chain:
                    dic[crt_filename] += chain.read()
                    self.save_notes += "\t- Used chain path %s\n" % chain_path
            else:
                self.save_notes += "\t- No chain path provided\n"

        with open(key_path) as key:
            self.save_notes += "\t- Used key path %s\n" % key_path
            dic[crt_filename] += key.read()

    def supported_enhancements(self):
        """Currently supported enhancements.

        Currently supports nothing. Possibilities: ['redirect', 'http-header',
        'ocsp-stapling', 'spdy'] (.certbot.constants.ENHANCEMENTS)

        :returns: List of supported enhancements.
        :rtype: list
        """
        return list(self._enhance_func.keys())

    def enhance(self, domain, enhancement, options=None):
        """Enhance configuration.

        :param str domain: domain to enhance
        :param str enhancement: enhancement type defined in
            :const:`~certbot.constants.ENHANCEMENTS`
        :param options: options for the enhancement
            See :const:`~certbot.constants.ENHANCEMENTS`
            documentation for appropriate parameter.

        :raises .errors.PluginError: If Enhancement is not supported, or if
            there is any other problem with the enhancement.

        """
        try:
            func = self._enhance_func[enhancement]
        except KeyError:
            raise errors.PluginError(
                "Unsupported enhancement: {0}".format(enhancement))
        try:
            func(domain, options)
        except errors.PluginError:
            logger.warn("Failed %s for %s", enhancement, domain)
            raise

    def save(self, title=None, temporary=False):
        """Saves all changes to the configuration files.

        This saves new files and file changes to the certificate directory.

        :param str title: The title of the save. If a title is given, the
            configuration will be saved as a new checkpoint and put in a
            timestamped directory.

        :param bool temporary: Indicates whether the changes made will
            be quickly reversed in the future (ie. challenges)

        :returns: True if successful
        :rtype: bool

        :raises .errors.PluginError: If there was an error in
            an attempt to save the configuration, or an error creating a
            checkpoint

        """
        logger.debug("save title: %s, temporary: %s", title, temporary)
        # The new files are the keys in the crt_files dictionary, their
        # content are the dict content.
        new_files = tuple(self.new_crt_files.keys())
        changed_files = tuple(self.crt_files.keys())

        try:
            # Create Checkpoint with changed files
            logger.debug("Adding changed files %s to reverter",
                         changed_files)
            if temporary:
                self.reverter.add_to_temp_checkpoint(
                    changed_files, self.save_notes)
            else:
                self.reverter.add_to_checkpoint(changed_files,
                                                self.save_notes)
            # Add new files
            if new_files:
                logger.debug("Adding new files %s to reverter", new_files)
                self.reverter.register_file_creation(temporary, *new_files)
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

        # Reset notes
        self.save_notes = ""

        # Write all new files and changes:
        for filepath, contents in \
                self.new_crt_files.items() + self.crt_files.items():

            # Make sure directory of filepath exists
            path = os.path.dirname(os.path.abspath(filepath))
            if not os.path.exists(path):
                os.makedirs(path)

            with open(filepath, 'w') as cert:
                cert.write(contents)
        self.new_crt_files = {}
        self.crt_files = {}

        # Finalize checkpoint
        if title and not temporary:
            try:
                self.reverter.finalize_checkpoint(title)
            except errors.ReverterError as err:
                raise errors.PluginError(str(err))

        return True

    def rollback_checkpoints(self, rollback=1):
        """Rollback saved checkpoints.

        :param int rollback: Number of checkpoints to revert

        :raises .errors.PluginError: If there is a problem with the input or
            the function is unable to correctly revert the configuration

        """
        try:
            self.reverter.rollback_checkpoints(rollback)
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

    def get_all_certs_keys(self):
        """Find all existing keys, certs from configuration. (Not implemented)

        :returns: list of tuples with form [(cert, key, path)]
            cert - str path to certificate file
            key - str path to associated key file
            path - File path to configuration file.
        :rtype: set
        """
        return list(self._get_certs_keys())

    def _get_certs_keys(self):
        """Generator for get_all_certs_keys"""
        for filepath in glob.glob(
                self.conf("haproxy-crt-dir") + '/*' + self.crt_postfix):
            with open(filepath) as pem:
                contents = pem.read()
                try:
                    cert = crypto.load_certificate(
                        crypto.FILETYPE_PEM, contents)
                    key = crypto.load_privatekey(crypto.FILETYPE_PEM, contents)
                    if cert.get_issuer().CN \
                            == self.conf('haproxy-ca-common-name') \
                            and key.check():
                        yield (filepath, filepath, self.conf("haproxy-config"))
                    else:
                        logger.info(
                            "CN %s is not %s, ignoring certificate %s",
                            cert.get_issuer().CN,
                            self.conf('haproxy-ca-common-name'),
                            filepath)

                except TypeError:
                    logger.warn("Could not read certificate, wrong type"
                                " (not PEM)")
                # Documentation says it raises "Error"
                except Exception, err:  # pylint: disable=broad-except
                    logger.error("Unexpected error! %s", err)

    def restart(self):
        """Runs a config test and restarts HAProxy.

        :raises .errors.MisconfigurationError: If either the config test
            or reload fails.

        """
        self.config_test()
        try:
            util.run_script(constants.os_constant("restart_cmd"))
        except errors.SubprocessError as err:
            raise errors.MisconfigurationError(str(err))

    def config_test(self):  # pylint: disable=no-self-use
        """Check the configuration of HAProxy for errors.

        :raises .errors.MisconfigurationError: If config_test fails

        """
        test_cmd = constants.os_constant('conftest_cmd') + \
            [constants.os_constant('haproxy_config')]
        print "Running test command: ", str(test_cmd)
        try:
            util.run_script(test_cmd)
        except errors.SubprocessError as err:
            raise errors.MisconfigurationError(str(err))
