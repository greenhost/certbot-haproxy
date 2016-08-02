"""HAProxy Configuration."""
import logging

import zope.component
import zope.interface

from acme import challenges

from certbot import errors
from certbot import interfaces
from certbot import util
from certbot import reverter

from certbot.plugins import common
# from certbot.plugins.util import path_surgery

from certbot_haproxy import constants

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@zope.interface.implementer(interfaces.IAuthenticator, interfaces.IInstaller)
@zope.interface.provider(interfaces.IPluginFactory)
class HAProxyConfigurator(common.Plugin):
    """
        HAProxy configurator.
    """

    description = "HAProxy - Alpha"

    @classmethod
    def add_parser_arguments(cls, add):
        # TODO: This is how we add arguments, do we need any?
        #add("enmod", default=constants.os_constant("enmod"),
        #    help="Path to the Apache 'a2enmod' binary.")
        pass

    def __init__(self, *args, **kwargs):
        """Initialize an Apache Configurator.

        :param tup version: version of Apache as a tuple (2, 4, 7)
            (used mostly for unittesting)

        """
        version = kwargs.pop("version", None)
        super(HAProxyConfigurator, self).__init__(*args, **kwargs)

        # Add name_server association dict
        self.assoc = dict()
        # Outstanding challenges
        self._chall_out = set()

        # No additional capabilities
        self._enhance_func = {}

        # Set up reverter
        self.reverter = reverter.Reverter(self.config)
        # TODO: Figure out what exactly it does and if it will work..
        self.reverter.recovery_routine()

    def prepare(self):
        """Prepare the authenticator/installer.
        """

        # Verify Apache is installed
        restart_cmd = constants.os_constant("restart_cmd")[0]
        if not util.exe_exists(restart_cmd):
            if not path_surgery(restart_cmd):
                raise errors.NoInstallationError(
                    'Cannot find HAProxy control command {0}'.format(
                        restart_cmd
                    )
                )

    def deploy_cert(self, domain, cert_path, key_path,
                    chain_path=None, fullchain_path=None):
        """
            Deploys certificate to HAProxy certificate store.

        :raises errors.PluginError: When unable to deploy certificate due to
            a lack of directives

        """
        vhost = self.choose_vhost(domain)
        self._clean_vhost(vhost)

        # This is done first so that ssl module is enabled and cert_path,
        # cert_key... can all be parsed appropriately
        self.prepare_server_https("443")

        path = {"cert_path": self.parser.find_dir("SSLCertificateFile",
                                                  None, vhost.path),
                "cert_key": self.parser.find_dir("SSLCertificateKeyFile",
                                                 None, vhost.path)}

        # Only include if a certificate chain is specified
        if chain_path is not None:
            path["chain_path"] = self.parser.find_dir(
                "SSLCertificateChainFile", None, vhost.path)

        if not path["cert_path"] or not path["cert_key"]:
            # Throw some can't find all of the directives error"
            logger.warn(
                "Cannot find a cert or key directive in %s. "
                "VirtualHost was not modified", vhost.path)
            # Presumably break here so that the virtualhost is not modified
            raise errors.PluginError(
                "Unable to find cert and/or key directives")

        logger.info("Deploying Certificate to VirtualHost %s", vhost.filep)
        logger.debug("Apache version is %s",
                     ".".join(str(i) for i in self.version))

        if self.version < (2, 4, 8) or (chain_path and not fullchain_path):
            # install SSLCertificateFile, SSLCertificateKeyFile,
            # and SSLCertificateChainFile directives
            set_cert_path = cert_path
            self.aug.set(path["cert_path"][-1], cert_path)
            self.aug.set(path["cert_key"][-1], key_path)
            if chain_path is not None:
                self.parser.add_dir(vhost.path,
                                    "SSLCertificateChainFile", chain_path)
            else:
                raise errors.PluginError("--chain-path is required for your "
                                         "version of Apache")
        else:
            if not fullchain_path:
                raise errors.PluginError("Please provide the --fullchain-path "
                                         "option pointing to your full chain f"
                                         "ile")
            set_cert_path = fullchain_path
            self.aug.set(path["cert_path"][-1], fullchain_path)
            self.aug.set(path["cert_key"][-1], key_path)

        # Save notes about the transaction that took place
        self.save_notes += ("Changed vhost at %s with addresses of %s\n"
                            "\tSSLCertificateFile %s\n"
                            "\tSSLCertificateKeyFile %s\n" %
                            (vhost.filep,
                             ", ".join(str(addr) for addr in vhost.addrs),
                             set_cert_path, key_path))
        if chain_path is not None:
            self.save_notes += "\tSSLCertificateChainFile %s\n" % chain_path

        # Make sure vhost is enabled if distro with enabled / available
        if self.conf("handle-sites"):
            if not vhost.enabled:
                self.enable_site(vhost)

    ######################################################################
    # Enhancements
    ######################################################################
    def supported_enhancements(self):  # pylint: disable=no-self-use
        """Returns currently supported enhancements."""
        return []

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
            func(self.choose_vhost(domain), options)
        except errors.PluginError:
            logger.warn("Failed %s for %s", enhancement, domain)
            raise

    def restart(self):
        """Runs a config test and reloads the Apache server.

        :raises .errors.MisconfigurationError: If either the config test
            or reload fails.

        """
        self.config_test()
        try:
            util.run_script(constants.os_constant("restart_cmd"))
        except errors.SubprocessError as err:
            raise errors.MisconfigurationError(str(err))

    def config_test(self):  # pylint: disable=no-self-use
        """Check the configuration of HaProxy for errors.

        :raises .errors.MisconfigurationError: If config_test fails

        """
        try:
            util.run_script(constants.os_constant("conftest_cmd"))
        except errors.SubprocessError as err:
            raise errors.MisconfigurationError(str(err))

    def get_version(self):
        """Return version of Apache Server.

        Version is returned as tuple. (ie. 2.4.7 = (2, 4, 7))

        :returns: version
        :rtype: tuple

        :raises .PluginError: if unable to find Apache version

        """
        try:
            stdout, _ = util.run_script(constants.os_constant("version_cmd"))
        except errors.SubprocessError:
            raise errors.PluginError(
                "Unable to run %s -v" %
                constants.os_constant("version_cmd"))

        regex = re.compile(r"Apache/([0-9\.]*)", re.IGNORECASE)
        matches = regex.findall(stdout)

        if len(matches) != 1:
            raise errors.PluginError("Unable to find Apache version")

        return tuple([int(i) for i in matches[0].split(".")])

    def more_info(self):
        """Human-readable string to help understand the module"""
        return (
            "Configures Apache to authenticate and install HTTPS.{0}"
            "Server root: {root}{0}"
            "Version: {version}".format(
                os.linesep, root=self.parser.loc["root"],
                version=".".join(str(i) for i in self.version))
        )

    ###########################################################################
    # Challenges Section
    ###########################################################################
    def get_chall_pref(self, unused_domain):  # pylint: disable=no-self-use
        """Return list of challenge preferences."""
        return [challenges.TLSSNI01]

    def perform(self, achalls):
        """Perform the configuration related challenge.

        This function currently assumes all challenges will be fulfilled.
        If this turns out not to be the case in the future. Cleanup and
        outstanding challenges will have to be designed better.

        """
        self._chall_out.update(achalls)
        responses = [None] * len(achalls)
        chall_doer = tls_sni_01.ApacheTlsSni01(self)

        for i, achall in enumerate(achalls):
            # Currently also have chall_doer hold associated index of the
            # challenge. This helps to put all of the responses back together
            # when they are all complete.
            chall_doer.add_chall(achall, i)

        sni_response = chall_doer.perform()
        if sni_response:
            # Must reload in order to activate the challenges.
            # Handled here because we may be able to load up other challenge
            # types
            self.restart()

            # TODO: Remove this dirty hack. We need to determine a reliable way
            # of identifying when the new configuration is being used.
            time.sleep(3)

            # Go through all of the challenges and assign them to the proper
            # place in the responses return value. All responses must be in the
            # same order as the original challenges.
            for i, resp in enumerate(sni_response):
                responses[chall_doer.indices[i]] = resp

        return responses

    def cleanup(self, achalls):
        """Revert all challenges."""
        self._chall_out.difference_update(achalls)

        # If all of the challenges have been finished, clean up everything
        if not self._chall_out:
            self.revert_challenge_config()
            self.restart()
            self.parser.init_modules()

    def revert_challenge_config(self):
        """Used to cleanup challenge configurations.

        :raises .errors.PluginError: If unable to revert the challenge config.

        """
        try:
            self.reverter.revert_temporary_config()
        except errors.ReverterError as err:
            raise errors.PluginError(str(err))
        self.parser.load()
