import sys

from setuptools import setup
from setuptools import find_packages

own_version = '0.1.2'
certbot_version = '0.8.1'

# Please update tox.ini when modifying dependency version requirements
install_requires = [
    'acme>={0}'.format(certbot_version),
    'certbot>={0}'.format(certbot_version),
    # For pkg_resources. >=1.0 so pip resolves it to a version cryptography
    # will tolerate; see #2599:
    'setuptools>=1.0',
    'zope.component',
    'zope.interface',
    'future',
]

if sys.version_info < (2, 7):
    install_requires.append('mock<1.1.0')
else:
    install_requires.append('mock')

docs_extras = [
    'Sphinx>=1.0',  # autodoc_member_order = 'bysource', autodoc_default_flags
    'sphinx_rtd_theme',
]

long_description = (
    "This is a plugin for Certbot, it enables automatically authenticating "
    "domains ans retrieving certificates. It can also restart HAProxy after "
    "new certificates are installed. However, it will not configure HAProxy "
    "because. HAProxy is unlikely to be used for small/simple setups like what"
    " Apache or NGiNX are more likely to be used for. HAProxy configurations "
    "vary greatly, any configuration this plugin could define is most likely "
    "not applicable in your environment."
)

haproxy_authenticator = 'certbot_haproxy.authenticator:HAProxyAuthenticator'
haproxy_installer = 'certbot_haproxy.installer:HAProxyInstaller'

setup(
    name='certbot-haproxy',
    version=own_version,
    description="HAProxy plugin for Certbot",
    long_description=long_description,
    url='https://code.greenhost.net/open/certbot-haproxy',
    author="Greenhost BV",
    author_email='lehaproxy@greenhost.net',
    license='Apache License 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'docs': docs_extras,
    },
    entry_points={
        'certbot.plugins': [
            'haproxy-authenticator = %s' % haproxy_authenticator,
            'haproxy-installer = %s' % haproxy_installer
        ],
    },
    # test_suite='certbot_haproxy',
)
