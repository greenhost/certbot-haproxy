"""HAProxy Authenticator."""
import logging

import zope.component
import zope.interface

from acme import challenges

from certbot import errors
from certbot import interfaces
from certbot import util
from certbot.plugins import standalone
# from certbot_haproxy import constants # for installer

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(standalone.Authenticator):
    """Standalone Authenticator.

    This authenticator creates its own ephemeral TCP listener on the
    necessary port in order to respond to incoming tls-sni-01 and http-01
    challenges from the certificate authority. Therefore, it does not
    rely on any existing server program.
    """

    description = "Certbot standalone authenticator with HAProxy preset."

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        # print self.config.__dict__

    @classmethod
    def add_parser_arguments(cls, add):
        """
            This method adds extra CLI arguments to the plugin.
            The arguments can be retrieved by asking for corresponding names
            in `self.conf([argument name])`
        """
        add(
            "internal-port",
            help=(
                "Port to open internally, you're expected to forward requests "
                "to port 80 to it."
            ),
            type=int,
            default=8080
        )

    @property
    def supported_challenges(self):
        """
            Challenges supported by this plugin: only HTTP01
        """
        return [challenges.HTTP01]

    @property
    def _necessary_ports(self):
        return {self.config.http01_port}

    def more_info(self):
        """
            TODO: Check that this statement is correct:
            This info string only appears in the curses UI in the plugin
            selection sequence.
        """
        return(
            "This authenticator creates its own ephemeral TCP listener "
            "on the configured internal port (default=8080) in order to "
            "respond to incoming http-01 challenges from the certificate "
            "authority. In order for this port to be reached, you need to "
            "configure HAProxy to forward any requests to any domain on the "
            "http-01 port (default:80), ending in `/.well-known/` to the "
            "http-01 port."
        )

    def prepare(self):  # pylint: disable=missing-docstring
        pass

    def get_chall_pref(self, domain):
        # pylint: disable=unused-argument,missing-docstring
        return self.supported_challenges
