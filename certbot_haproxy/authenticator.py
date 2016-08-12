"""
    HAProxy Authenticator.

    This authenticator creates its own ephemeral TCP listener on the necessary
    port in order to respond to incoming http-01 challenges from the
    certificate authority. You need to forward port requests for
    `/.well-known/acme-challenge/` on port 80 to the http-01 port
    (default:8000). You may do this like this for example:

    ```
        default_backend nodes

        acl is_cerbot path_beg -i /.well-known/acme-challenge
        use_backend certbot if is_cerbot

        backend certbot
            log global
            mode http
            server certbot 127.0.0.1:8000

        backend nodes
            log global
            mode http
            option tcplog
            balance roundrobin
            option forwardfor
            option http-server-close
            option httpclose
            http-request set-header X-Forwarded-Port %[dst_port]
            http-request add-header X-Forwarded-Proto https if { ssl_fc }
            option httpchk HEAD / HTTP/1.1\r\nHost:localhost
            server node1 127.0.0.1:8080 check
            server node2 127.0.0.1:8080 check
            server node3 127.0.0.1:8080 check
            server node4 127.0.0.1:8080 check
    ```

    The Authenticator of this plugin is simply an extension of the "standalone"
    plugin that is part of certbot. It limits its functionality to only support
    the http-01 challenge because checks the challenge by connecting to port
    443. We can't proxy requests to certbot because we can't see the requested
    uri until the request is decrypted, and we can't do decryption in HAProxy
    because tls-sni-01 expects to do a TLS handshake.
"""
import logging

import zope.component
import zope.interface

from acme import challenges

from certbot import interfaces
from certbot.plugins import standalone
# from certbot_haproxy import constants # for installer

logger = logging.getLogger(__name__)  # pylint:disable=invalid-name


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(standalone.Authenticator):
    """Standalone Authenticator."""

    description = "Certbot standalone authenticator with HAProxy preset."

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.config.http01_port = self.conf('internal_port')
        self.add_parser_arguments()

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
        add(
            "internal-port",
            help=(
                "Port to open internally, you're expected to forward requests"
                " to port 80 to it."
            ),
            type=int,
            default=8000
        )

    @property
    def supported_challenges(self):
        """
            Challenges supported by this plugin: only http-01
            See introduction for reasoning.
        """
        return [challenges.HTTP01]

    def more_info(self):
        """
            This info string only appears in the curses UI in the plugin
            selection sequence.
        """
        return (
            "This authenticator creates its own ephemeral TCP listener"
            " on the configured internal port (default=8000) in order to"
            " respond to incoming http-01 challenges from the certificate"
            " authority. In order for this port to be reached, you need to"
            " configure HAProxy to forward any requests to any domain on the"
            " http-01 port (default:80), ending in"
            " `/.well-known/acme-challenge/` to the http-01 port (hint:8000)."
        )
