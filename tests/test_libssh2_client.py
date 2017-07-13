import unittest
import os
import logging

from embedded_server.openssh import OpenSSHServer
from pssh.libssh2_client import SSHClient, logger as ssh_logger


PKEY_FILENAME = os.path.sep.join([os.path.dirname(__file__), 'client_pkey'])

ssh_logger.setLevel(logging.DEBUG)
logging.basicConfig()


class LibSSH2ClientTest(unittest.TestCase):

    def __init__(self, methodname):
        unittest.TestCase.__init__(self, methodname)
        self.fake_cmd = 'echo me'
        self.fake_resp = 'me'
        self.user_key = PKEY_FILENAME
        self.host = '127.0.0.1'
        self.port = 2222
        self.server = OpenSSHServer()
        self.server.start_server()
        self.client = SSHClient(self.host, port=self.port,
                                pkey=PKEY_FILENAME,
                                num_retries=1)

    def test_execute(self):
        channel, host, stdout, stderr, stdin = self.client.exec_command(
            self.fake_cmd)
        self.client.join()
        output = list(stdout)
        stderr = list(stderr)
        expected = [self.fake_resp]
        exit_code = channel.exit_status()
        self.assertEqual(exit_code, 0)
        self.assertEqual(expected, output)

    def test_stderr(self):
        channel, host, stdout, stderr, stdin = self.client.exec_command(
            'echo "me" >&2')
        self.client.join()
        output = list(stdout)
        stderr = list(stderr)
