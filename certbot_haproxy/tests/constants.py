import unittest
from mock import patch
from certbot.errors import NotSupportedError
from certbot_haproxy import constants


class ConstantsTest(unittest.TestCase):
    """
        Test that the right constants are chosen and the correct warnings are
        given or Exceptions are raised.
    """

    CLI_DEFAULTS = {
        "debian": {
            '_min_version': '7',
            '_max_version': '8',
            '7': 7,
            '8': 8
        },
        "ubuntu": {
            '_min_version': '14.04',
            '_max_version': '16.04',
            '14.04': 1404,
            '14.10': 1410,
            '15.04': 1504,
            '15.10': 1510,
            '16.04': 1604
        }
    }

    @patch('constants.CLI_DEFAULTS', return_value=CLI_DEFAULTS)
    @patch('certbot.util.get_os_info', return_value=['debian', '8'])
    def test_os_analyse_supported(self, *mocks):
        """ Test a supported version.. """
        self.assertEqual(
            constants.os_analyse(caching_disabled=True),
            ('debian', '8')
        )

    @patch('constants.CLI_DEFAULTS', return_value=CLI_DEFAULTS)
    @patch('certbot.util.get_os_info', return_value=['debian', '9'])
    @patch('certbot_haproxy.constants.logger')
    def test_os_analyse_unsupported_new(self, m_logger, *mocks):
        """ Test an unsupported, too new version.. """
        self.assertEqual(
            constants.os_analyse(caching_disabled=True),
            ('debian', '8')
        )
        m_logger.warn.assert_called_once()

    @patch('constants.CLI_DEFAULTS', return_value=CLI_DEFAULTS)
    @patch('certbot.util.get_os_info', return_value=['debian', '6'])
    def test_os_analyse_unsupported_old(self, *mocks):
        """ Test an unsupported too old version.. """
        with self.assertRaises(NotSupportedError):
            constants.os_analyse(caching_disabled=True)

    @patch('constants.CLI_DEFAULTS', return_value=CLI_DEFAULTS)
    @patch('certbot.util.get_os_info', return_value=['centos', '7'])
    def test_os_analyse_unsupported_distro(self, *mocks):
        """ Test an unsupported OS/distro.. """
        with self.assertRaises(NotSupportedError):
            constants.os_analyse(caching_disabled=True)

    @patch('constants.CLI_DEFAULTS', return_value=CLI_DEFAULTS)
    @patch('certbot.util.get_os_info', return_value=['ubuntu', '15.06'])
    @patch('certbot_haproxy.constants.logger')
    def test_os_analyse_between_versions(self, m_logger, *mocks):
        """ Test a version in between our supported version numbers.. """
        self.assertEqual(
            constants.os_analyse(caching_disabled=True),
            ('ubuntu', '15.04')
        )
        m_logger.warn.assert_called_once()


if __name__ == '__main__':
    unittest.main()
