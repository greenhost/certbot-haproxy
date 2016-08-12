"""
    HAProxy Installer.

    This installer combines the certificate files into one file and places them
    in the specified directory so HAProxy can use them.
"""
import logging

import zope.component
import zope.interface

from certbot import interfaces

from certbot import errors
from certbot import util
from certbot import reverter
from certbot.plugins import common
from certbot_haproxy import constants

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@zope.interface.implementer(interfaces.IInstaller)
@zope.interface.provider(interfaces.IPluginFactory)
class HAProxyInstaller(common.Plugin):
    """HAProxy Installer."""

    description = "Certbot installer for HAProxy."

    def __init__(self, *args, **kwargs):
        super(HAProxyInstaller, self).__init__(*args, **kwargs)
        self.reverter = reverter.Reverter(self.config)
        self.restart_cmd = constants.os_constant("restart_cmd")[0]

    @classmethod
    def add_parser_arguments(cls, add):
        """
            This method adds extra CLI arguments to the plugin.
            The arguments can be retrieved by asking for corresponding names
            in `self.conf([argument name])`

            NOTE: This is an override a method defined in the parent, we are
            deliberately not calling super() because it would add arguments
            that we don't support.
        """
        pass

    @staticmethod
    def more_info():
        """
            This info string only appears in the curses UI in the plugin
            selection sequence.
        """
        return (
            "This installer combines the certificate files into one file and"
            " places them in the specified directory so HAProxy can use them."
        )

    def get_all_names(self):
        return ['testsite.nl', 'mrtndwrd.nl']

    def view_config_changes(self):
        """Show all of the configuration changes that have taken place.

        :raises .errors.PluginError: If there is a problem while processing
            the checkpoints directories.

        """
        try:
            self.reverter.view_config_changes()
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

    def prepare(self):
        """
            Check that we can restart HAProxy when we are done.
        """
        if not util.exe_exists(self.restart_cmd):
            raise errors.NoInstallationError(
                'Cannot find HAProxy control command {0}'.format(
                    self.restart_cmd
                )
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

    def deploy_cert(self, domain, cert_path, key_path,
                    chain_path=None, fullchain_path=None):
        pass

    def supported_enhancements(self, *args, **kwargs):
        print "supported_enhancements"
        print args
        print kwargs

    def config_test(self, *args, **kwargs):
        print "config_test"
        print args
        print kwargs

    def enhance(self, *args, **kwargs):
        print "enhance"
        print args
        print kwargs

    def save(self, title=None, temporary=False):
        """Saves all changes to the configuration files.

        :param str title: The title of the save. If a title is given, the
            configuration will be saved as a new checkpoint and put in a
            timestamped directory.

        :param bool temporary: Indicates whether the changes made will
            be quickly reversed in the future (ie. challenges)

        :raises .errors.PluginError: If there was an error in
            an attempt to save the configuration, or an error creating a
            checkpoint

        """
        save_files = set(self.parser.parsed.keys())

        try:
            # Create Checkpoint
            if temporary:
                self.reverter.add_to_temp_checkpoint(
                    save_files, self.save_notes)
            else:
                self.reverter.add_to_checkpoint(save_files,
                                            self.save_notes)
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))

        self.save_notes = ""

        # Change 'ext' to something else to not override existing conf files
        self.parser.filedump(ext='')
        if title and not temporary:
            try:
                self.reverter.finalize_checkpoint(title)
            except errors.ReverterError as err:
                raise errors.PluginError(str(err))

        return True

    def rollback_checkpoints(self, *args, **kwargs):
        print "rollback_checkpoints"
        print args
        print kwargs

    def get_all_certs_keys(self, *args, **kwargs):
        print "get_all_certs_keys"
        print args
        print kwargs

    def restart(self, *args, **kwargs):
        print "restart"
        print args
        print kwargs

#    def deploy_cert(self, domain, cert_path, key_path,
#                    chain_path=None, fullchain_path=None):
#        """
#            Deploys certificate to HAProxy certificate store.
#
#        :raises errors.PluginError: When unable to deploy certificate due to
#            a lack of directives
#
#        """
#        vhost = self.choose_vhost(domain)
#        self._clean_vhost(vhost)
#
#        # This is done first so that ssl module is enabled and cert_path,
#        # cert_key... can all be parsed appropriately
#        self.prepare_server_https("443")
#
#        path = {"cert_path": self.parser.find_dir("SSLCertificateFile",
#                                                  None, vhost.path),
#                "cert_key": self.parser.find_dir("SSLCertificateKeyFile",
#                                                 None, vhost.path)}
#
#        # Only include if a certificate chain is specified
#        if chain_path is not None:
#            path["chain_path"] = self.parser.find_dir(
#                "SSLCertificateChainFile", None, vhost.path)
#
#        if not path["cert_path"] or not path["cert_key"]:
#            # Throw some can't find all of the directives error"
#            logger.warn(
#                "Cannot find a cert or key directive in %s. "
#                "VirtualHost was not modified", vhost.path)
#            # Presumably break here so that the virtualhost is not modified
#            raise errors.PluginError(
#                "Unable to find cert and/or key directives")
#
#        logger.info("Deploying Certificate to VirtualHost %s", vhost.filep)
#        logger.debug("Apache version is %s",
#                     ".".join(str(i) for i in self.version))
#
#        if self.version < (2, 4, 8) or (chain_path and not fullchain_path):
#            # install SSLCertificateFile, SSLCertificateKeyFile,
#            # and SSLCertificateChainFile directives
#            set_cert_path = cert_path
#            self.aug.set(path["cert_path"][-1], cert_path)
#            self.aug.set(path["cert_key"][-1], key_path)
#            if chain_path is not None:
#                self.parser.add_dir(vhost.path,
#                                    "SSLCertificateChainFile", chain_path)
#            else:
#                raise errors.PluginError("--chain-path is required for your "
#                                         "version of Apache")
#        else:
#            if not fullchain_path:
#                raise errors.PluginError("Please provide the --fullchain-path "
#                                         "option pointing to your full chain f"
#                                         "ile")
#            set_cert_path = fullchain_path
#            self.aug.set(path["cert_path"][-1], fullchain_path)
#            self.aug.set(path["cert_key"][-1], key_path)
#
#        # Save notes about the transaction that took place
#        self.save_notes += ("Changed vhost at %s with addresses of %s\n"
#                            "\tSSLCertificateFile %s\n"
#                            "\tSSLCertificateKeyFile %s\n" %
#                            (vhost.filep,
#                             ", ".join(str(addr) for addr in vhost.addrs),
#                             set_cert_path, key_path))
#        if chain_path is not None:
#            self.save_notes += "\tSSLCertificateChainFile %s\n" % chain_path
#
#        # Make sure vhost is enabled if distro with enabled / available
#        if self.conf("handle-sites"):
#            if not vhost.enabled:
#                self.enable_site(vhost)
#
#    ######################################################################
#    # Enhancements
#    ######################################################################
#    def supported_enhancements(self):  # pylint: disable=no-self-use
#        """Returns currently supported enhancements."""
#        return []
#
#    def enhance(self, domain, enhancement, options=None):
#        """Enhance configuration.
#
#        :param str domain: domain to enhance
#        :param str enhancement: enhancement type defined in
#            :const:`~certbot.constants.ENHANCEMENTS`
#        :param options: options for the enhancement
#            See :const:`~certbot.constants.ENHANCEMENTS`
#            documentation for appropriate parameter.
#
#        :raises .errors.PluginError: If Enhancement is not supported, or if
#            there is any other problem with the enhancement.
#
#        """
#        try:
#            func = self._enhance_func[enhancement]
#        except KeyError:
#            raise errors.PluginError(
#                "Unsupported enhancement: {0}".format(enhancement))
#        try:
#            func(self.choose_vhost(domain), options)
#        except errors.PluginError:
#            logger.warn("Failed %s for %s", enhancement, domain)
#            raise
#
#    def restart(self):
#        """Runs a config test and reloads the Apache server.
#
#        :raises .errors.MisconfigurationError: If either the config test
#            or reload fails.
#
#        """
#        self.config_test()
#        try:
#            util.run_script(constants.os_constant("restart_cmd"))
#        except errors.SubprocessError as err:
#            raise errors.MisconfigurationError(str(err))
#
#    def config_test(self):  # pylint: disable=no-self-use
#        """Check the configuration of HaProxy for errors.
#
#        :raises .errors.MisconfigurationError: If config_test fails
#
#        """
#        try:
#            util.run_script(constants.os_constant("conftest_cmd"))
#        except errors.SubprocessError as err:
#            raise errors.MisconfigurationError(str(err))
#
#    def get_version(self):
#        """Return version of Apache Server.
#
#        Version is returned as tuple. (ie. 2.4.7 = (2, 4, 7))
#
#        :returns: version
#        :rtype: tuple
#
#        :raises .PluginError: if unable to find Apache version
#
#        """
#        try:
#            stdout, _ = util.run_script(constants.os_constant("version_cmd"))
#        except errors.SubprocessError:
#            raise errors.PluginError(
#                "Unable to run %s -v" %
#                constants.os_constant("version_cmd"))
#
#        regex = re.compile(r"Apache/([0-9\.]*)", re.IGNORECASE)
#        matches = regex.findall(stdout)
#
#        if len(matches) != 1:
#            raise errors.PluginError("Unable to find Apache version")
#
#        return tuple([int(i) for i in matches[0].split(".")])
#
#    def more_info(self):
#        """Human-readable string to help understand the module"""
#        return (
#            "Configures Apache to authenticate and install HTTPS.{0}"
#            "Server root: {root}{0}"
#            "Version: {version}".format(
#                os.linesep, root=self.parser.loc["root"],
#                version=".".join(str(i) for i in self.version))
#        )
#
#
#)



#    def prepare(self):
#        """Prepare the authenticator/installer.
#        """
#
#        # Verify Apache is installed
#        restart_cmd = constants.os_constant("restart_cmd")[0]
#        if not util.exe_exists(restart_cmd):
#            if not path_surgery(restart_cmd):
#                raise errors.NoInstallationError(
#                    'Cannot find HAProxy control command {0}'.format(
#                        restart_cmd
#                    )
#                )
#
#    def deploy_cert(self, domain, cert_path, key_path,
#                    chain_path=None, fullchain_path=None):
#        """
#            Deploys certificate to HAProxy certificate store.
#
#        :raises errors.PluginError: When unable to deploy certificate due to
#            a lack of directives
#
#        """
#        vhost = self.choose_vhost(domain)
#        self._clean_vhost(vhost)
#
#        # This is done first so that ssl module is enabled and cert_path,
#        # cert_key... can all be parsed appropriately
#        self.prepare_server_https("443")
#
#        path = {"cert_path": self.parser.find_dir("SSLCertificateFile",
#                                                  None, vhost.path),
#                "cert_key": self.parser.find_dir("SSLCertificateKeyFile",
#                                                 None, vhost.path)}
#
#        # Only include if a certificate chain is specified
#        if chain_path is not None:
#            path["chain_path"] = self.parser.find_dir(
#                "SSLCertificateChainFile", None, vhost.path)
#
#        if not path["cert_path"] or not path["cert_key"]:
#            # Throw some can't find all of the directives error"
#            logger.warn(
#                "Cannot find a cert or key directive in %s. "
#                "VirtualHost was not modified", vhost.path)
#            # Presumably break here so that the virtualhost is not modified
#            raise errors.PluginError(
#                "Unable to find cert and/or key directives")
#
#        logger.info("Deploying Certificate to VirtualHost %s", vhost.filep)
#        logger.debug("Apache version is %s",
#                     ".".join(str(i) for i in self.version))
#
#        if self.version < (2, 4, 8) or (chain_path and not fullchain_path):
#            # install SSLCertificateFile, SSLCertificateKeyFile,
#            # and SSLCertificateChainFile directives
#            set_cert_path = cert_path
#            self.aug.set(path["cert_path"][-1], cert_path)
#            self.aug.set(path["cert_key"][-1], key_path)
#            if chain_path is not None:
#                self.parser.add_dir(vhost.path,
#                                    "SSLCertificateChainFile", chain_path)
#            else:
#                raise errors.PluginError("--chain-path is required for your "
#                                         "version of Apache")
#        else:
#            if not fullchain_path:
#                raise errors.PluginError("Please provide the --fullchain-path "
#                                         "option pointing to your full chain f"
#                                         "ile")
#            set_cert_path = fullchain_path
#            self.aug.set(path["cert_path"][-1], fullchain_path)
#            self.aug.set(path["cert_key"][-1], key_path)
#
#        # Save notes about the transaction that took place
#        self.save_notes += ("Changed vhost at %s with addresses of %s\n"
#                            "\tSSLCertificateFile %s\n"
#                            "\tSSLCertificateKeyFile %s\n" %
#                            (vhost.filep,
#                             ", ".join(str(addr) for addr in vhost.addrs),
#                             set_cert_path, key_path))
#        if chain_path is not None:
#            self.save_notes += "\tSSLCertificateChainFile %s\n" % chain_path
#
#        # Make sure vhost is enabled if distro with enabled / available
#        if self.conf("handle-sites"):
#            if not vhost.enabled:
#                self.enable_site(vhost)
#
#    ######################################################################
#    # Enhancements
#    ######################################################################
#    def supported_enhancements(self):  # pylint: disable=no-self-use
#        """Returns currently supported enhancements."""
#        return []
#
#    def enhance(self, domain, enhancement, options=None):
#        """Enhance configuration.
#
#        :param str domain: domain to enhance
#        :param str enhancement: enhancement type defined in
#            :const:`~certbot.constants.ENHANCEMENTS`
#        :param options: options for the enhancement
#            See :const:`~certbot.constants.ENHANCEMENTS`
#            documentation for appropriate parameter.
#
#        :raises .errors.PluginError: If Enhancement is not supported, or if
#            there is any other problem with the enhancement.
#
#        """
#        try:
#            func = self._enhance_func[enhancement]
#        except KeyError:
#            raise errors.PluginError(
#                "Unsupported enhancement: {0}".format(enhancement))
#        try:
#            func(self.choose_vhost(domain), options)
#        except errors.PluginError:
#            logger.warn("Failed %s for %s", enhancement, domain)
#            raise
#
#    def restart(self):
#        """Runs a config test and reloads the Apache server.
#
#        :raises .errors.MisconfigurationError: If either the config test
#            or reload fails.
#
#        """
#        self.config_test()
#        try:
#            util.run_script(constants.os_constant("restart_cmd"))
#        except errors.SubprocessError as err:
#            raise errors.MisconfigurationError(str(err))
#
#    def config_test(self):  # pylint: disable=no-self-use
#        """Check the configuration of HaProxy for errors.
#
#        :raises .errors.MisconfigurationError: If config_test fails
#
#        """
#        try:
#            util.run_script(constants.os_constant("conftest_cmd"))
#        except errors.SubprocessError as err:
#            raise errors.MisconfigurationError(str(err))
#
#    def get_version(self):
#        """Return version of Apache Server.
#
#        Version is returned as tuple. (ie. 2.4.7 = (2, 4, 7))
#
#        :returns: version
#        :rtype: tuple
#
#        :raises .PluginError: if unable to find Apache version
#
#        """
#        try:
#            stdout, _ = util.run_script(constants.os_constant("version_cmd"))
#        except errors.SubprocessError:
#            raise errors.PluginError(
#                "Unable to run %s -v" %
#                constants.os_constant("version_cmd"))
#
#        regex = re.compile(r"Apache/([0-9\.]*)", re.IGNORECASE)
#        matches = regex.findall(stdout)
#
#        if len(matches) != 1:
#            raise errors.PluginError("Unable to find Apache version")
#
#        return tuple([int(i) for i in matches[0].split(".")])
#
#    def more_info(self):
#        """Human-readable string to help understand the module"""
#        return (
#            "Configures Apache to authenticate and install HTTPS.{0}"
#            "Server root: {root}{0}"
#            "Version: {version}".format(
#                os.linesep, root=self.parser.loc["root"],
#                version=".".join(str(i) for i in self.version))
#        )
#
#
