"""Test installer functions"""
from past.builtins import basestring
import unittest
import mock
import os

from certbot import errors
from certbot.plugins import common
from certbot_haproxy.installer import HAProxyInstaller


def _conf(self, var):
    """Don't append names to attributes in the config."""
    return getattr(self.config, var.replace("-", "_"))


@mock.patch("certbot_haproxy.installer.HAProxyInstaller.conf", new=_conf)
class TestInstaller(unittest.TestCase):

    test_domain = 'le.wtf'

    """Test the relevant functions of the certbot_haproxy installer"""

    def setUp(self):
        self.test_dir = "installer"
        self.temp_dir, config_dir, work_dir = common.dir_setup(
            test_dir=self.test_dir,
            pkg="certbot_haproxy.tests")
        backups = os.path.join(work_dir, "backups")
        mock_le_config = mock.MagicMock(
            temp_checkpoint_dir=os.path.join(
                work_dir, "temp_checkpoints"),
            in_progress_dir=os.path.join(backups, "IN_PROGRESS"),
            work_dir=work_dir,
            config_dir=config_dir,
            temp_dir=self.temp_dir,
            backup_dir=backups,
            haproxy_config=os.path.join(
                self.temp_dir, self.test_dir, "haproxy.cfg"),
            haproxy_crt_dir=os.path.join(
                self.temp_dir, self.test_dir, "certs"),
            haproxy_ca_common_name=u'h2ppy h2cker fake CA',
            no_fall_back_cert=False,
        )

        self.installer = HAProxyInstaller(
            config=mock_le_config, name="installer")
        self.installer.prepare()

    def test_get_all_certs_keys(self):
        """Test if get_all_certs_keys returns all the LE certificates"""
        all_certs_keys = self.installer.get_all_certs_keys()
        self.assertEqual(len(all_certs_keys), 3)
        self.assertIsInstance(all_certs_keys, list)
        for item in all_certs_keys:
            self.assertIsInstance(item, tuple)

    @mock.patch("certbot_haproxy.installer.logger")
    @mock.patch("certbot.util.logger")
    def test_add_parser_arguments(self, util_logger, certbot_logger):
        """Weak test taken from apache plugin tests"""
        self.installer.add_parser_arguments(mock.MagicMock())
        self.assertEqual(certbot_logger.error.call_count, 0)
        self.assertEqual(util_logger.error.call_count, 0)

    def test_get_all_names(self):
        """Tests if get_all_Names reads le1.wtf and le2.wtf from the test
        haproxy config file
        """
        names = self.installer.get_all_names()
        self.assertEqual(names, set(['le1.wtf', 'le2.wtf']))

    def test_fall_back_cert(self, *mocks):
        """Test if a certificate is generated and added to new_crt_files"""
        # Should maybe use another library than OpenSSL, if that's possible
        from OpenSSL import crypto
        self.installer.new_crt_files = {}
        self.installer._fall_back_cert()
        key = list(self.installer.new_crt_files.keys())[0]
        cert = self.installer.new_crt_files[key]
        self.assertIsInstance(key, str)
        self.assertIsInstance(cert, str)
        privkey = crypto.load_privatekey(crypto.FILETYPE_PEM, cert)
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        self.assertTrue(privkey.check())

    def test_deploy_cert_save(self):
        """Deploy and save a certificate and rollback after that"""
        # Variables for test:
        crt_dir = os.path.join(self.temp_dir, self.test_dir, "deploy_test")
        base = os.path.join(self.temp_dir, self.test_dir, "deploy_cert")
        key_path = os.path.join(base, "privkey.pem")
        cert_path = os.path.join(base, "cert.pem")
        chain_path = os.path.join(base, "chain.pem")
        fullchain_path = os.path.join(base, "fullchain.pem")

        # Prepare installer
        self.installer.config.no_fall_back_cert = True
        self.installer.config.haproxy_crt_dir = crt_dir

        # Try with files that don't exist, should raise PluginError:
        self.assertRaises(
            errors.PluginError,
            self.installer.deploy_cert,
            self.test_domain, 'no-cert', 'no-key')

        # Arguments for several tests
        all_args = [
            (self.test_domain, cert_path, key_path),
            (self.test_domain, cert_path, key_path, chain_path),
            (self.test_domain, None, key_path, None, fullchain_path),
        ]

        # Run deploy and save with all types of args
        for args in all_args:
            # Deploy with only key and cert
            self.installer.deploy_cert(*args)

            try:
                self.installer.view_config_changes()
            except ReverterError:
                self.fail("Reverter failed")
            except PluginError:
                self.fail("Reverter failed with PluginError")

            self.installer.save()
            # Check if le.wtf.pem is created
            pem = os.path.join(crt_dir, self.test_domain) \
                + self.installer.crt_postfix
            self.assertTrue(os.path.isfile(pem))
            # Roll back pem creation
            self.installer.rollback_checkpoints()
            # Check if file was removed again
            self.assertFalse(os.path.isfile(pem))

        # Try to revert:
        try:
            self.installer.recovery_routine()
        except PluginError:
            self.fail("Recovery routine didn't work")

        # fail without key
        self.assertRaises(
            errors.PluginError,
            self.installer.deploy_cert,
            self.test_domain, cert_path, None)

        # Run twice (should update instead of create)
        args = (self.test_domain, cert_path, key_path)
        self.installer.deploy_cert(*args)
        self.installer.save()
        self.installer.deploy_cert(*args)
        self.installer.save()


    def test_enhancement(self):
        """ Currently no enhancements are supported, we should see that """
        self.assertRaises(
            errors.PluginError,
            self.installer.enhance,
            self.test_domain,
            "non-existent-enhancement")


    @mock.patch("certbot_haproxy.installer.logger")
    @mock.patch("certbot.util.logger")
    def test_config_test(self, util_logger, certbot_logger):
        """Test config_test function with a faulty and a valid cfg file"""
        # Check with bad config file
        self.installer.config.haproxy_config = os.path.join(
            self.temp_dir, self.test_dir, "haproxy_bad.cfg")
        self.assertRaises(
            errors.MisconfigurationError,
            self.installer.config_test
        )

        # Check with empty config file
        self.installer.config.haproxy_config = os.path.join(
            self.temp_dir, self.test_dir, "haproxy_empty.cfg")
        self.assertRaises(
            errors.MisconfigurationError,
            self.installer.config_test
        )

    def test_more_info(self):
        ret = self.installer.more_info()
        self.assertIsInstance(ret, basestring)

    @mock.patch('certbot.util.exe_exists', return_value=False)
    def test_failed_service_command(self, mock_exe_exists):
        """ Fail on service manager command """
        self.assertRaises(errors.NoInstallationError, self.installer.prepare)
        mock_exe_exists.assert_called_once()

    @mock.patch('subprocess.check_output',
                return_value='not-really-a-version-number')
    def test_no_version_number(self, mock_check_output):
        """ Fail on version command """
        self.assertRaises(errors.NoInstallationError, self.installer.prepare)

    @mock.patch('subprocess.check_output', 
                return_value='HA-Proxy version 1.4.8 2014/10/31')
    def test_wrong_version_number(self, mock_check_output):
        """ Supply a too low version number for HAproxy """
        self.assertRaises(errors.NotSupportedError, self.installer.prepare)
        mock_check_output.assert_called_once()
