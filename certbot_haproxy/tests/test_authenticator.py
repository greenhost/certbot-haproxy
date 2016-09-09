import unittest
import mock
import os

from certbot_haproxy.authenticator import HAProxyAuthenticator
from acme import challenges

class TestAuthenticator(unittest.TestCase):

    test_domain = 'le.wtf'

    """Test the relevant functions of the certbot_haproxy installer"""

    def setUp(self):
        mock_le_config = mock.MagicMock(
            # TODO: Don't know what we need here
            )
        self.authenticator = HAProxyAuthenticator(
            config=mock_le_config, name="authenticator")

    def test_more_info(self):
        info = self.authenticator.more_info()
        self.assertIsInstance(info, str)

    @mock.patch("certbot_haproxy.authenticator.logger")
    @mock.patch("certbot.util.logger")
    def test_add_parser_arguments(self, util_logger, certbot_logger):
        """Weak test taken from apache plugin tests"""
        self.authenticator.add_parser_arguments(mock.MagicMock())
        self.assertEqual(certbot_logger.error.call_count, 0)
        self.assertEqual(util_logger.error.call_count, 0)

    def test_supported_challenges(self):
        chal = self.authenticator.supported_challenges
        self.assertIsInstance(chal, list)
        self.assertTrue(challenges.HTTP01 in chal)
