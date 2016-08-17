"""Test installer functions"""
import unittest
import mock
import os

from certbot_haproxy.installer import HAProxyInstaller
from certbot.plugins import common


def _conf(self, var):
    """Don't append names to attributes in the config."""
    return getattr(self.config, var.replace("-", "_"))


class TestInstaller(unittest.TestCase):

    def setUp(self):
        test_dir = "installer"
        temp_dir, config_dir, work_dir = common.dir_setup(
            test_dir=test_dir,
            pkg="certbot_haproxy.tests")
        backups = os.path.join(work_dir, "backups")
        mock_le_config = mock.MagicMock(
            temp_checkpoint_dir=os.path.join(
                work_dir, "temp_checkpoints"),
            in_progress_dir=os.path.join(backups, "IN_PROGRESS"),
            work_dir=work_dir,
            config_dir=config_dir,
            temp_dir=temp_dir,
            haproxy_config="/etc/haproxy/config",
            haproxy_crt_dir=os.path.join(temp_dir, test_dir, "certs"),
            haproxy_ca_common_name=u'h2ppy h2cker fake CA'
        )

        with mock.patch("certbot.reverter.Reverter"):
            self.installer = HAProxyInstaller(
                config=mock_le_config, name="installer")
        self.installer.prepare()

    @mock.patch("certbot_haproxy.installer.HAProxyInstaller.conf",
                new=_conf)
    def test_get_all_certs_keys(self):
        """Test if get_all_certs_keys returns all the LE certificates"""
        all_certs_keys = self.installer.get_all_certs_keys()
        self.assertEqual(len(all_certs_keys), 3)
        self.assertIsInstance(all_certs_keys, list)
        for item in all_certs_keys:
            self.assertIsInstance(item, tuple)
