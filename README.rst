HAProxy plugin for Certbot
==========================

Getting started (development)
-----------------------------

In order to run tests against the Let's Encrypt API we will run a Boulder
server, which is the exact same server Let's Encrypt is running. The server is
started in Virtual Box using Vagrant. To prevent the installation of any
components and dependencies from cluttering up your computer there is also a
client Virtual Box instance. Both of these machines can be setup and started by
running the `dev_start.sh` script.

Running locally without sudo
----------------------------

You can't run certbot without root privileges because it needs to access
`/etc/letsencrypt`, however you can tell it not to use `/etc/` and use some
other path in your home directory.

```
mkdir ~/projects/cerbot-haproxy/working
mkdir ~/projects/cerbot-haproxy/working/config
mkdir ~/projects/cerbot-haproxy/working/logs
cat <<EOF >> ~/.config/letsencrypt/cli.ini
work-dir=~/projects/certbot-haproxy/working/
logs-dir=~/projects/certbot-haproxy/working/logs/
config-dir=~/projects/certbot-haproxy/working/config
EOF
```

Now you can run cerbot without root privileges.

Further time savers during development..
----------------------------------------
The following options can be saved in the `cli.ini` file for the following
reasons.

 - `agree-tos`: During each request for a certificate you need to agree to the
   terms of service of Let's Encrypt, automatically accept them every time.
 - `no-self-upgrade`: Tell LE to not upgrade itself. Could be very annoying
   when stuff starts to suddenly break, that worked just fine before.
 - `register-unsafely-without-email`: Tell LE that you don't want to be
   notified by e-mail when certificates are about to expire or when the TOS
   changes, if you don't you will need to enter a valid e-mail address for
   every test run.
 - `text`: Disable the curses UI, and use the plain CLI version instead.
 - `domain example.org`: Enter a default domain name to request a certificate
   for, so you don't have to specify it every time.
 - `configurator certbot-haproxy:haproxy`: Test with the HAProxy plugin every
   time.



cat <<EOF >> ~/.config/letsencrypt/cli.ini
agree-tos
no-self-upgrade
register-unsafely-without-email
text
domain example.org
configurator certbot-haproxy:haproxy
EOF


Setuptools version conflict
---------------------------

Most likely the `python-setuptools` version in your os's repositories is quite
outdated. You will need to install a newer version, to do this you can run:

```
pip install --upgrade setuptools
```

Since pip is part of `python-setuptools`, you need to have it installed before
you can update.
