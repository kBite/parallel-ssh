# This file is part of parallel-ssh.

# Copyright (C) 2014-2017 Panos Kittenis

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, version 2.1.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""LibSSH2 based SSH client package"""

import socket
import logging
import os
import pwd
from socket import gaierror as sock_gaierror, error as sock_error

from gevent import sleep
from gevent.select import select
import libssh2

from .exceptions import UnknownHostException, AuthenticationException, \
     ConnectionErrorException, SSHException
from .constants import DEFAULT_RETRIES

host_logger = logging.getLogger('pssh.host_logger')
logger = logging.getLogger('pssh')


class WrapperChannel(libssh2.Channel):
    """Wrapper class over :mod:`libssh2.Channel` with functions for getting
    exit status"""

    def __init__(self, _channel):
        libssh2.Channel.__init__(self, _channel)

    def exit_status_ready(self):
        return True if self.exit_status() else False

    def recv_exit_status(self):
        return self.exit_status()


class SSHClient(object):
    """Low level libssh2 based SSH client"""

    LIBSSH2_ERROR_EAGAIN = -37
    IDENTITIES = [
        '~/.ssh/id_dsa',
        '~/.ssh/id_rsa',
        '~/.ssh/identity'
    ]

    def __init__(self, host,
                 user=None, password=None, port=None,
                 private_key_file=None, # forward_ssh_agent=True,
                 num_retries=DEFAULT_RETRIES): # agent=None, timeout=10,
                 # proxy_host=None, proxy_port=22):
        self.host = host
        self.user = user if user else pwd.getpwuid(os.getuid()).pw_name
        self.password = password
        self.port = port if port else 22
        self.private_key_file = private_key_file
        # self.forward_ssh_agent = forward_ssh_agent
        self.num_retries = num_retries
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(1)
        self.sock.connect_ex((self.host, self.port))
        self.sock.setblocking(0)
        self.session = libssh2.Session()
        self.session.setblocking(0)
        self.startup()
        self.auth()
        self.channel = self.open_channel()

    def startup(self):
        return self._eagain(self.session.startup, self.sock)

    def _agent_auth(self):
        self.session.setblocking(1)
        self.session.userauth_agent(self.user)
        self.session.setblocking(0)

    def _identity_auth(self):
        for identity_file in self.IDENTITIES:
            pk_file = os.path.expanduser(identity_file)
            if not os.path.isfile(pk_file):
                continue
            pub_file = "%s.pub" % (identity_file)
            pub_file = os.path.expanduser(pub_file)
            try:
                if not self._eagain(self.session.userauth_publickey_fromfile,
                                    self.user,
                                    pub_file,
                                    pk_file,
                                    self.password):
                    continue
            except Exception as ex:
                logger.debug("Authentication with identity file %s failed, "
                             "continuing with other identities",
                             identity_file)
                continue
            else:
                logger.debug("Authentication succeeded with identity file %s",
                             identity_file)
                return
        raise AuthenticationException("No authentication methods succeeded")

    def auth(self):
        try:
            self._agent_auth()
        except Exception as ex:
            logger.debug("Agent auth failed with %s, "
                         "continuing with other authentication methods",
                         ex)
        else:
            logger.debug("Authentication with SSH Agent succeeded")
            return
        self._identity_auth()

    def open_channel(self):
        chan = self.session.open_session()
        while chan is None:
            self._wait_select()
            chan = self.session.open_session()
        return chan

    def __del__(self):
        self._eagain(self.session.close)

    def _run_with_retries(self, func, count=0, *args, **kwargs):
        while func(*args, **kwargs) == self.LIBSSH2_ERROR_EAGAIN:
            if count > self.num_retries:
                raise AuthenticationException(
                    "Error authenticating %s@%s", self.user, self.host,)
            count += 1

    def get_transport(self):
        return self.session

    def _eagain(self, func, *args, **kwargs):
        ret = func(*args, **kwargs)
        while ret == self.LIBSSH2_ERROR_EAGAIN:
            self._wait_select()
            ret = func(*args, **kwargs)
        return ret

    def execute(self, channel, cmd):
        channel.execute(cmd)
        remainder = ""
        while not channel.eof():
            self._wait_select()
            _size, _data = channel.read_ex()
            if _size == 0 or _data is None:
                break
            _pos = 0
            _data = remainder + _data
            while _pos < _size:
                linesep = _data.find(os.linesep, _pos)
                if linesep > 0:
                    yield _data[_pos:linesep].strip()
                    _pos = linesep + 1
                else:
                    remainder = _data[_pos:]
                    break
        # channel.close()

    def _wait_select(self):
        """
        Find out from libssh2 if its blocked on read or write and wait
        accordingly.
        Return immediately if libssh2 is not blocked
        """
        blocked = self.session.blockdirections()
        if blocked == 0:
            return
        readfds = [self.sock] if (blocked & 01) else ()
        writefds = [self.sock] if (blocked & 02) else ()
        select(readfds, writefds, [])

    def exec_command(self, command, sudo=False, user=None,
                     use_pty=True):
        if use_pty:
            self._eagain(self.channel.pty)
        return WrapperChannel(self.channel), self.host, \
            self.execute(self.channel, command), iter([])

# list(client.execute(client.session.open_session(), 'ls -ltrh'))
