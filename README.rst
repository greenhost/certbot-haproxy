HAProxy plugin for Certbot
==========================

.. contents:: Table of Contents

About
-----

This is a certbot plugin for using certbot in combination with a HAProxy setup.
Its advantage over using the standalone certbot is that it automatically places
certificates in the correct directory and restarts HAProxy afterwards. It should
also enable you to very easily do automatic certificate renewal.

Furthermore, you can configure HAProxy to handle Boulder's authentication using
the HAProxy authenticator of this plugin.

It was created for use with `Greenhost's`_ shared hosting environment and can be
useful to you in the following cases:

- If you use HAProxy and have several domains for which you want to enable Let's
  Encrypt certificates.
- If you yourself have a shared hosting platform that uses HAProxy to redirect
  to your client's websites.
- Actually any case in which you want to automatically restart HAProxy after you
  request a new certificate.

.. _Greenhost's: https://greenhost.net

This plugin does not configure HAProxy for you, because HAProxy configurations
can can vary a great deal. Please read the installation instructions on how to
configure HAProxy for use with the plugin. If you have a good idea on how we can
implement automatic HAProxy configuration, you are welcome to create a merge
request or an issue.

Installing: Requirements
------------------------

Currently this plugin has been tested on Debian Jessie, but it will most likely
work on Ubuntu 14.04+ too. If you are running Debian Wheezy, you may need to
take additional steps during the installation. Thus, the requirements are:

- Debian Jessie (or higher) or Ubuntu Trusty (or higher).
- Python 2.7 (2.6 is supported by certbot and our goal is to be compatible but
  it has not been tested yet).
- HAProxy 1.6+ (we will configure SNI, which is not strictly required)
- Certbot 0.8+

Installing:
-----------

If you need to set up a server, follow the instructions in the
`</FULL_INSTALL.rst>`_ document. If you only need to install the certbot-haproxy
plugin and already have HAProxy running on a server, keep reading.

Quick installation
++++++++++++++++++

If you already have a server running HAProxy, first install certbot following
their `installation instructions <https://certbot.eff.org/docs/install.html>`_.
Then follow these steps to install certbot-haproxy:

.. code:: bash

    git clone https://code.greenhost.net/open/certbot-haproxy.git
    cd ./certbot-haproxy/
    sudo pip install ./

.. _haproxy_config:
Configuring HAProxy to work with certbot-haproxy
------------------------------------------------

Let's Encrypt's CA server will try to contact your proxy on port 80, which is
most likely in use for your and/or your customers' websites. So we have
configured our plugin to open port ``8000`` to verify control over the domain
instead. Therefore we need to forward verification requests on port 80 to port
8000 internally.

The sample below contains all that is required for a working load-balancing
HAProxy setup that also forwards these verification requests. But it is
probably not "copy-paste compatible" with your setup. So you need to piece
together a configuration that works for you.

.. code::

    cat <<EOF > /etc/haproxy/haproxy.cfg
    global
        log /dev/log local0
        log /dev/log local1 notice
        chroot /var/lib/haproxy
        stats socket /run/haproxy/admin.sock mode 660 level admin
        stats timeout 30s
        user haproxy
        group haproxy
        daemon

        # Default ciphers to use on SSL-enabled listening sockets.
        # Cipher suites chosen by following logic:
        #  - Bits of security 128>256 (weighing performance vs added security)
        #  - Key exchange: EECDH>DHE (faster first)
        #  - Mode: GCM>CBC (streaming cipher over block cipher)
        #  - Ephemeral: All use ephemeral key exchanges
        #  - Explicitly disable weak ciphers and SSLv3
        ssl-default-bind-ciphers AES128+AESGCM+EECDH+SHA256:AES128+EECDH:AES128+AESGCM+DHE:AES128+EDH:AES256+AESGCM+EECDH:AES256+EECDH:AES256+AESGCM+EDH:AES256+EDH:-SHA:AES128+AESGCM+EECDH+SHA256:AES128+EECDH:AES128+AESGCM+DHE:AES128+EDH:AES256+AESGCM+EECDH:AES256+EECDH:AES256+AESGCM+EDH:AES256+EDH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!3DES:!DSS
        #ssl-default-bind-options no-sslv3 no-tls-tickets force-tlsv12
        ssl-default-bind-options no-sslv3 no-tls-tickets
        ssl-dh-param-file /opt/certbot/dhparams.pem

    defaults
        log     global
        mode    http
        option  httplog
        option  dontlognull
        timeout connect 5000
        timeout client  50000
        timeout server  50000
        errorfile 400 /etc/haproxy/errors/400.http
        errorfile 403 /etc/haproxy/errors/403.http
        errorfile 408 /etc/haproxy/errors/408.http
        errorfile 500 /etc/haproxy/errors/500.http
        errorfile 502 /etc/haproxy/errors/502.http
        errorfile 503 /etc/haproxy/errors/503.http
        errorfile 504 /etc/haproxy/errors/504.http

    frontend http-in
        # Listen on port 80
        bind \*:80
        # Listen on port 443
        # Uncomment after running certbot for the first time, a certificate
        # needs to be installed *before* HAProxy will be able to start when this
        # directive is not commented.
        #
        bind \*:443 ssl crt /opt/certbot/haproxy_fullchains/__fallback.pem crt /opt/certbot/haproxy_fullchains

        # Forward Certbot verification requests to the certbot-haproxy plugin
        acl is_certbot path_beg -i /.well-known/acme-challenge
        rspadd Strict-Transport-Security:\ max-age=31536000;\ includeSubDomains;\ preload
        rspadd X-Frame-Options:\ DENY
        use_backend certbot if is_certbot
        # The default backend is a cluster of 4 Apache servers that you need to
        # host.
        default_backend nodes

    backend certbot
        log global
        mode http
        server certbot 127.0.0.1:8000

        # You can also configure separate domains to force a redirect from port 80
        # to 443 like this:
        # redirect scheme https if !{ ssl_fc } and [PUT YOUR DOMAIN NAME HERE]

    backend nodes
        log global
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
        # If redirection from port 80 to 443 is to be forced, uncomment the next
        # line. Keep in mind that the bind \*:443 line should be uncommented and a
        # certificate should be present for all domains
        redirect scheme https if !{ ssl_fc }

    EOF

    systemctl restart haproxy

Running certbot-haproxy
-----------------------

Now you can try to run Certbot with the plugin as the Authenticator and
Installer, if you already have websites configured in your HAProxy setup, you
may try to install a certificate now.

.. code:: bash

    certbot run --authenticator certbot-haproxy:haproxy-authenticator \
        --installer certbot-haproxy:haproxy-installer

If you want your ``certbot`` to always use our Installer and Authenticator, you
can add this to your configuration file:

.. code:: bash

    cat <<EOF >> $HOME/.config/letsencrypt/cli.ini
    authenticator=certbot-haproxy:haproxy-authenticator
    installer=certbot-haproxy:haproxy-installer
    EOF

If you need to run in unattended mode, there are a bunch of arguments you need
to set in order for Certbot to generate a certificate for you.

- ``--domain [DOMAIN NAME]`` The domain name you want SSL to be enabled for.
- ``--agree-tos`` Tell Certbot you agree with its `TOS`_
- ``--email [EMAIL ADDRESS]`` An e-mail address where issues with certificates
  can be sent to, as well as changes in the `TOS`_. Or you could supply
  ``--register-unsafely-without-email`` but this is not recommended.

.. _TOS: https://letsencrypt.org/documents/LE-SA-v1.1.1-August-1-2016.pdf

After you run certbot successfully once, there will be 2 certificate files in
the certificate directory. This is a pre-requisite for HAProxy to start with
the ``bind *:443 [..]`` directive in the configuration.

You can auto renew certificates by using the systemd service and timer below.
They are set to run every 12 hours because certificates that *will not* expire
soon will not be replaced but certificates that *will* expire soon, will be
replaced in a timely manner. The timer also starts the renewal process 2
minutes after the server boots, this is done so renewal starts immediately
after the server has been offline for a long time.

.. code:: bash

    cat <<EOF > /etc/systemd/system/letsencrypt.timer
    [Unit]
    Description=Run Let's Encrypt every 12 hours

    [Timer]
    # Time to wait after booting before we run first time
    OnBootSec=2min
    # Time between running each consecutive time
    OnUnitActiveSec=12h
    Unit=letsencrypt.service

    [Install]
    WantedBy=timers.target
    EOF

    cat <<EOF > /etc/systemd/system/letsencrypt.service
    [Unit]
    Description=Renew Let's Encrypt Certificates

    [Service]
    Type=simple
    User=certbot
    ExecStart=/usr/bin/certbot renew -q
    EOF

    # Enable the timer and start it, this is not necessary for the service,
    # since the timer starts it.
    systemctl enable letsencrypt.timer
    systemctl start letsencrypt.timer


Development
-----------

For development guidelines, check `</CONTRIBUTING.rst>`_
