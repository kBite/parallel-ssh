.. contents::


Advanced Usage
=================

There are several more advanced use cases of `ParallelSSH`, such as tunneling (aka proxying) via an intermediate SSH server and per-host configuration and command substitution among others.

Agents and Private Keys
*************************

SSH Agent forwarding
-----------------------

SSH agent forwarding, what ``ssh -A`` does on the command line, is supported and enabled by default. Creating a client object as:

.. code-block:: python

   ParallelSSHClient(hosts, forward_ssh_agent=False)

will disable this behaviour.

Programmatic Private Keys
--------------------------

By default, ``ParallelSSH`` will use all keys in an available SSH agent and identity keys under the user's SSH directory - ``id_rsa`` and ``id_dsa`` in ``~/.ssh``.

A private key can also be provided programmatically.

.. code-block:: python

  from pssh.utils import load_private_key
  from pssh import ParallelSSHClient

  client = ParallelSSHClient(hosts, pkey=load_private_key('my_key'))

Where ``my_key`` is a private key file in current working directory.

The helper function :py:func:`load_private_key <pssh.utils.load_private_key>` will attempt to load all available key types and raises :mod:`SSHException <pssh.exceptions.SSHException>` if it cannot load the key file.

.. seealso::

   :py:func:`load_private_key <pssh.utils.load_private_key>`

Disabling use of system SSH Agent
----------------------------------

Use of an available SSH agent can also be disabled.

.. code-block:: python

  client = ParallelSSHClient(hosts, pkey=load_private_key('my_key'), 
                             allow_agent=False)

.. warning::

   For large number of hosts, it is recommended that private keys are provided programmatically and use of SSH agent is disabled via ``allow_agent=False`` as above. 

   If the number of hosts is large enough, available connections to the system SSH agent may be exhausted which will stop the client from working on a subset of hosts.

   This is a limitation of the underlying SSH client used by ``ParallelSSH``.

Programmatic SSH Agent
-----------------------

It is also possible to programmatically provide an SSH agent for the client to use, instead of a system provided one. This is useful in cases where hosts need different private keys and a system SSH agent is not available.

.. code-block:: python
   
   from pssh.agent import SSHAgent
   from pssh.utils import load_private_key
   from pssh import ParallelSSHClient

   agent = SSHAgent()
   agent.add_key(load_private_key('my_private_key_filename'))
   agent.add_key(load_private_key('my_other_private_key_filename'))
   hosts = ['my_host', 'my_other_host']

   client = ParallelSSHClient(hosts, agent=agent)
   client.run_command(<..>)

.. note::

   Supplying an agent programmatically implies that a system SSH agent will *not* be used even if available.

.. seealso::

   :py:class:`pssh.agent.SSHAgent`


Tunneling
**********

This is used in cases where the client does not have direct access to the target host and has to authenticate via an intermediary, also called a bastion host, commonly used for additional security as only the bastion host needs to have access to the target host.

ParallelSSHClient       ------>        Proxy host         -------->         Target host

Proxy host can be configured as follows in the simplest case:

.. code-block:: python

  hosts = [<..>]
  client = ParallelSSHClient(hosts, proxy_host='bastion')
  
Configuration for the proxy host's user name, port, password and private key can also be provided, separate from target host user name.

.. code-block:: python
   
   from pssh.utils import load_private_key
   
   hosts = [<..>]
   client = ParallelSSHClient(hosts, user='target_host_user', 
                              proxy_host='bastion', proxy_user='my_proxy_user',
 			      proxy_port=2222, 
 			      proxy_pkey=load_private_key('proxy.key'))

Where ``proxy.key`` is a filename containing private key to use for proxy host authentication.

In the above example, connections to the target hosts are made via ``my_proxy_user@bastion:2222`` -> ``target_host_user@<host>``.

.. note::

   Proxy host connections are asynchronous and use the SSH protocol's native TCP tunneling - aka local port forward. No external commands or processes are used for the proxy connection, unlike the `ProxyCommand` directive in OpenSSH and other utilities.

   While connections initiated by ``ParallelSSH`` are asynchronous, connections from proxy host -> target hosts may not be, depending on SSH server implementation. If only one proxy host is used to connect to a large number of target hosts and proxy SSH server connections are *not* asynchronous, this may adversely impact performance on the proxy host.

Per-Host Configuration
***********************

Sometimes, different hosts require different configuration like user names and passwords, ports and private keys. Capability is provided to supply per host configuration for such cases.

.. code-block:: python

   from pssh.utils import load_private_key

   host_config = {'host1' : {'user': 'user1', 'password': 'pass',
                             'port': 2222,
                             'private_key': load_private_key(
                                 'my_key.pem')},
                  'host2' : {'user': 'user2', 'password': 'pass',
		             'port': 2223,
			     'private_key': load_private_key(
			         open('my_other_key.pem'))},
		 }
   hosts = host_config.keys()

   client = ParallelSSHClient(hosts, host_config=host_config)
   client.run_command('uname')
   <..>

In the above example, ``host1`` will use user name ``user1`` and private key from ``my_key.pem`` and ``host2`` will use user name ``user2`` and private key from ``my_other_key.pem``.

.. note::

   Proxy host cannot be provided via per-host configuration at this time.

Per-Host Command substitution
******************************

For cases where different commands should be run on each host, or the same command with different arguments, functionality exists to provide per-host command arguments for substitution.

The ``host_args`` keyword parameter to :py:func:`run_command <pssh.pssh_client.ParallelSSHClient.run_command>` can be used to provide arguments to use to format the command string.

Number of ``host_args`` items should be at least as many as number of hosts.

Any Python string format specification characters may be used in command string.


In the following example, first host in hosts list will use cmd ``host1_cmd`` second host ``host2_cmd`` and so on

.. code-block:: python
   
   output = client.run_command('%s', host_args=('host1_cmd',
                                                'host2_cmd',
						'host3_cmd',))

Command can also have multiple arguments to be substituted.

.. code-block:: python

   output = client.run_command('%s %s',
   host_args=(('host1_cmd1', 'host1_cmd2'),
              ('host2_cmd1', 'host2_cmd2'),
	      ('host3_cmd1', 'host3_cmd2'),))

A list of dictionaries can also be used as ``host_args`` for named argument substitution.

In the following example, first host in host list will use cmd ``host-index-0``, second host ``host-index-1`` and so on.

.. code-block:: python

   host_args=[{'cmd': 'host-index-%s' % (i,))
              for i in range(len(client.hosts))]
   output = client.run_command('%(cmd)s', host_args=host_args)


Run command features and options
*********************************

See :py:func:`run_command API documentation <pssh.pssh_client.ParallelSSHClient.run_command>` for a complete list of features and options.

.. note::

   With a PTY, the default, stdout and stderr output is combined into stdout.

   Without a PTY, separate output is given for stdout and stderr, although some programs and server configurations require a PTY.

Run with sudo
---------------

``ParallelSSH`` can be instructed to run its commands under ``sudo``:

.. code-block:: python

   client = <..>
   
   output = client.run_command(<..>, sudo=True)
   client.join(output)

While not best practice and password-less `sudo` is best configured for a limited set of commands, a sudo password may be provided via the stdin channel:

.. code-block:: python

   client = <..>
   
   output = client.run_command(<..>, sudo=True)
   for host in output:
       stdin = output[host].stdin
       stdin.write('my_password\n')
       stdin.flush()
   client.join(output)

Output encoding
-----------------

By default, output is encoded as ``UTF-8``. This can be configured with the ``encoding`` keyword argument.

.. code-block:: python

   client = <..>

   client.run_command(<..>, encoding='utf-16')
   stdout = list(output[client.hosts[0]].stdout)

Contents of ``stdout`` will be `UTF-16` encoded.

.. note::
   
   Encoding must be valid `Python codec <https://docs.python.org/2.7/library/codecs.html>`_

Disabling use of pseudo terminal emulation
--------------------------------------------

By default, ``ParallelSSH`` uses the user's configured shell to run commands with. As a shell is used by default, a pseudo terminal (`PTY`) is also requested by default.

For cases where use of a `PTY` is not wanted, such as having separate stdout and stderr outputs, the remote command is a daemon that needs to fork and detach itself or when use of a shell is explicitly disabled, use of PTY can also be disabled.

The following example prints to stderr with PTY disabled.

.. code-block:: python

   from __future__ import print_function

   client = <..>

   client.run_command("echo 'asdf' >&2", use_pty=False)
   for line in output[client.hosts[0]].stderr: 
       print(line)

:Output:
   .. code-block:: shell

      asdf

Combined stdout/stderr
-----------------------

With a PTY, stdout and stderr output is combined.

The same example as above with a PTY:

.. code-block:: python

   from __future__ import print_function

   client = <..>

   client.run_command("echo 'asdf' >&2")
   for line in output[client.hosts[0]].stdout: 
       print(line)

Note output is now from the ``stdout`` channel.

:Output:
   .. code-block:: shell

      asdf

Stderr is empty:

.. code-block:: python
   
   for line in output[client.hosts[0]].stderr:
       print(line)

No output from ``stderr``.

SFTP
*****

SFTP - `SCP version 2` - is supported by ``Parallel-SSH`` and two functions are provided by the client for copying files with SFTP.

SFTP does not have a shell interface and no output is provided for any SFTP commands.

As such, SFTP functions in ``ParallelSSHClient`` return greenlets that will need to be joined to raise any exceptions from them. :py:func:`gevent.joinall` may be used for that.


Copying files to remote hosts in parallel
----------------------------------------------

To copy the local file with relative path ``../test`` to the remote relative path ``test_dir/test`` - remote directory will be created if it does not exist, permissions allowing. ``raise_error=True`` instructs ``joinall`` to raise any exceptions thrown by the greenlets.

.. code-block:: python

   from pssh.pssh_client import ParallelSSHClient
   from gevent import joinall
   
   client = ParallelSSHClient(hosts)
   
   greenlets = client.copy_file('../test', 'test_dir/test')
   joinall(greenlets, raise_error=True)

To recursively copy directory structures, enable the ``recurse`` flag:

.. code-block:: python

   greenlets = client.copy_file('my_dir', 'my_dir', recurse=True)
   joinall(greenlets, raise_error=True)

.. seealso::

   :py:func:`copy_file <pssh.pssh_client.ParallelSSHClient.copy_file>` API documentation and exceptions raised.

   :py:func:`gevent.joinall` Gevent's ``joinall`` API documentation.

Copying files from remote hosts in parallel
----------------------------------------------

Copying remote files in parallel requires that file names are de-duplicated otherwise they will overwrite each other. ``copy_remote_file`` names local files as ``<local_file><suffix_separator><host>``, suffixing each file with the host name it came from, separated by a configurable character or string.

.. code-block:: python

   from pssh.pssh_client import ParallelSSHClient
   from gevent import joinall
   
   client = ParallelSSHClient(hosts)
   
   greenlets = client.copy_remote_file('remote.file', 'local.file')
   joinall(greenlets, raise_error=True)

The above will create files ``local.file_host1`` where ``host1`` is the host name the file was copied from.

.. seealso::

   :py:func:`copy_remote_file <pssh.pssh_client.ParallelSSHClient.copy_remote_file>`  API documentation and exceptions raised.

Single host copy
-----------------

If wanting to copy a file from a single remote host and retain the original filename, can use the single host :py:class:`SSHClient <pssh.ssh_client.SSHClient>` and its :py:func:`copy_file <pssh.ssh_client.SSHClient.copy_remote_file>` directly.

.. code-block:: python

   from pssh.ssh_client import SSHClient
   
   client = SSHClient('localhost')
   client.copy_remote_file('remote_filename', 'local_filename')

.. seealso::

   :py:func:`SSHClient.copy_remote_file <pssh.ssh_client.SSHClient.copy_remote_file>`  API documentation and exceptions raised.


Hosts filtering and overriding
*******************************

Iterators and filtering
------------------------

Any type of iterator may be used as hosts list, including generator and list comprehension expressions.

:List comprehension:
   .. code-block:: python

      hosts = ['dc1.myhost1', 'dc2.myhost2']
      client = ParallelSSHClient([h for h in hosts if h.find('dc1')])

:Generator:
   .. code-block:: python

      hosts = ['dc1.myhost1', 'dc2.myhost2']
      client = ParallelSSHClient((h for h in hosts if h.find('dc1')))
    
:Filter:
   .. code-block:: python

      hosts = ['dc1.myhost1', 'dc2.myhost2']
      client = ParallelSSHClient(filter(lambda h: h.find('dc1'), hosts))
      client.run_command(<..>)

.. note ::

    Since generators by design only iterate over a sequence once then stop, ``client.hosts`` should be re-assigned after each call to ``run_command`` when using generators as target of ``client.hosts``.

Overriding hosts list
----------------------

Hosts list can be modified in place. A call to ``run_command`` will create new connections as necessary and output will only contain output for the hosts ``run_command`` executed on.

.. code-block:: python

   client = <..>

   client.hosts = ['otherhost']
   print(client.run_command('exit 0'))
   {'otherhost': exit_code=None, <..>}
