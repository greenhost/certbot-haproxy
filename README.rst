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
work-dir=/home/chris/projects/certbot-haproxy/working/
logs-dir=/home/chris/projects/certbot-haproxy/working/logs/
config-dir=/home/chris/projects/certbot-haproxy/working/config
EOF
```

Now you can run cerbot without root privileges.
