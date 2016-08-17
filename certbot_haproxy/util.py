"""
    Utility functions.
"""

from OpenSSL import crypto
import socket


class MemoiseNoArgs(object):  # pylint:disable=too-few-public-methods
    """
        Remember the output of a function with NO arguments so it does not have
        to be determined after the first time it's called.
    """
    def __init__(self, function):
        self.function = function
        self.memo = None

    def __call__(self, caching_disabled=False):
        if self.memo is None or caching_disabled:
            self.memo = self.function()
        return self.memo


class Memoise(object):  # pylint:disable=too-few-public-methods
    """
        Remember the output of a function with NO arguments so it does not have
        to be determined after the first time it's called.
    """
    def __init__(self, function):
        self.function = function
        self.memo = {}

    def __call__(self, caching_disabled=False, *args):
        if args not in self.memo or caching_disabled:
            self.memo[args] = self.function(*args)
        return self.memo[args]


def create_self_signed_cert(bits=2048, **kwargs):
    """
        Create a self-signed certificate
    """
    # Generate private/public key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, bits)

    # Set X.509 attributes and self-sign
    cert = crypto.X509()

    attributes = {
        'countryName': u"FU",
        'stateOrProvinceName': u"Oceania",
        'localityName': u"London",
        'organizationName': u"Ministry of Truth",
        'organizationalUnitName': u"Ministry of Truth",
        'commonName': socket.gethostname()
    }

    subject = cert.get_subject()
    for attribute, default in attributes.items():
        subject.__setattr__(attribute, kwargs.pop(attribute, default))

    cert.set_serial_number(kwargs.pop('serialnr', 1984))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(315360000)  # 10*365*24*60*60
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    return (
        crypto.dump_privatekey(crypto.FILETYPE_PEM, key),
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    )
