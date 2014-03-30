# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import hashlib

from requests_oauthlib import OAuth1, OAuth1Session
from requests_oauthlib.oauth1_auth import CONTENT_TYPE_FORM_URLENCODED, to_native_str
from oauthlib.common import extract_params, generate_nonce, generate_timestamp, log, urlparse, Request
from oauthlib.oauth1 import Client, SIGNATURE_HMAC, SIGNATURE_TYPE_AUTH_HEADER, SIGNATURE_PLAINTEXT, SIGNATURE_RSA, \
    SIGNATURE_TYPE_BODY
from oauthlib.oauth1.rfc5849 import signature


class BodyHashOAuth1Session(OAuth1Session):
    def __init__(self, client_key,
                 client_secret=None,
                 resource_owner_key=None,
                 resource_owner_secret=None,
                 callback_uri=None,
                 signature_method=SIGNATURE_HMAC,
                 signature_type=SIGNATURE_TYPE_AUTH_HEADER,
                 rsa_key=None,
                 verifier=None):
        __doc__ = super(BodyHashOAuth1Session, self).__init__.__doc__

        # Skip OAuth1Session.__init__ since we're duplicating its functionality
        super(OAuth1Session, self).__init__()
        self._client = BodyHashOAuth1(client_key,
                                      client_secret=client_secret,
                                      resource_owner_key=resource_owner_key,
                                      resource_owner_secret=resource_owner_secret,
                                      callback_uri=callback_uri,
                                      signature_method=signature_method,
                                      signature_type=signature_type,
                                      rsa_key=rsa_key,
                                      verifier=verifier)
        self.auth = self._client


class BodyHashOAuth1(OAuth1):
    def __init__(self, client_key,
                 client_secret=None,
                 resource_owner_key=None,
                 resource_owner_secret=None,
                 callback_uri=None,
                 signature_method=SIGNATURE_HMAC,
                 signature_type=SIGNATURE_TYPE_AUTH_HEADER,
                 rsa_key=None, verifier=None,
                 decoding='utf-8'):

        try:
            signature_type = signature_type.upper()
        except AttributeError:
            pass

        self.client = BodyHashClient(client_key, client_secret, resource_owner_key,
                                     resource_owner_secret, callback_uri, signature_method,
                                     signature_type, rsa_key, verifier, decoding=decoding)

    def __call__(self, r):
        """Add OAuth parameters to the request.

        Parameters may be included from the body if the content-type is
        urlencoded, if no content type is set a guess is made.
        """
        # Overwriting url is safe here as request will not modify it past
        # this point.

        content_type = r.headers.get('Content-Type', '')
        if not content_type and extract_params(r.body):
            content_type = CONTENT_TYPE_FORM_URLENCODED
        if not isinstance(content_type, unicode):
            content_type = content_type.decode('utf-8')

        is_form_encoded = (CONTENT_TYPE_FORM_URLENCODED in content_type)

        if is_form_encoded:
            r.headers['Content-Type'] = CONTENT_TYPE_FORM_URLENCODED
            r.url, headers, r.body = self.client.sign(
                unicode(r.url), unicode(r.method), r.body or '', r.headers)
        else:
            r.url, headers, _ = self.client.sign(
                unicode(r.url), unicode(r.method), r.body or '', r.headers)

        r.prepare_headers(headers)
        r.url = to_native_str(r.url)
        return r


class BodyHashClient(Client):

    def get_oauth_params(self, request):
        __doc__ = Client.get_oauth_params.__doc__
        nonce = (generate_nonce()
                 if self.nonce is None else self.nonce)
        timestamp = (generate_timestamp()
                     if self.timestamp is None else self.timestamp)
        params = [
            ('oauth_nonce', nonce),
            ('oauth_timestamp', timestamp),
            ('oauth_version', '1.0'),
            ('oauth_signature_method', self.signature_method),
            ('oauth_consumer_key', self.client_key),
            ]
        if self.resource_owner_key:
            params.append(('oauth_token', self.resource_owner_key))
        else:
            params.append(('oauth_body_hash', self.hash_body(request)))
        if self.callback_uri:
            params.append(('oauth_callback', self.callback_uri))
        if self.verifier:
            params.append(('oauth_verifier', self.verifier))

        return params

    def hash_body(self, request):
        if self.signature_method in (SIGNATURE_HMAC, SIGNATURE_RSA):
            return base64.b64encode(hashlib.sha1(request.body).digest())
        raise ValueError('Invalid signature method.')


    def sign(self, uri, http_method='GET', body=None, headers=None, realm=None):
        __doc__ = Client.sign.__doc__

        # normalize request data
        request = Request(uri, http_method, body, headers,
                          encoding=self.encoding)

        # sanity check
        content_type = request.headers.get('Content-Type', None)
        multipart = content_type and content_type.startswith('multipart/')
        should_have_params = content_type == CONTENT_TYPE_FORM_URLENCODED
        has_params = request.decoded_body is not None
        # 3.4.1.3.1.  Parameter Sources
        # [Parameters are collected from the HTTP request entity-body, but only
        # if [...]:
        #    *  The entity-body is single-part.
        if multipart and has_params:
            raise ValueError("Headers indicate a multipart body but body contains parameters.")
        #    *  The entity-body follows the encoding requirements of the
        #       "application/x-www-form-urlencoded" content-type as defined by
        #       [W3C.REC-html40-19980424].
        elif should_have_params and not has_params:
            raise ValueError("Headers indicate a formencoded body but body was not decodable.")
        #    *  The HTTP request entity-header includes the "Content-Type"
        #       header field set to "application/x-www-form-urlencoded".
        elif not should_have_params and has_params:
            raise ValueError("Body contains parameters but Content-Type header was not set.")

        # 3.5.2.  Form-Encoded Body
        # Protocol parameters can be transmitted in the HTTP request entity-
        # body, but only if the following REQUIRED conditions are met:
        # o  The entity-body is single-part.
        # o  The entity-body follows the encoding requirements of the
        #    "application/x-www-form-urlencoded" content-type as defined by
        #    [W3C.REC-html40-19980424].
        # o  The HTTP request entity-header includes the "Content-Type" header
        #    field set to "application/x-www-form-urlencoded".
        elif self.signature_type == SIGNATURE_TYPE_BODY and not (
                        should_have_params and has_params and not multipart):
            raise ValueError('Body signatures may only be used with form-urlencoded content')

        # We amend http://tools.ietf.org/html/rfc5849#section-3.4.1.3.1
        # with the clause that parameters from body should only be included
        # in non GET or HEAD requests. Extracting the request body parameters
        # and including them in the signature base string would give semantic
        # meaning to the body, which it should not have according to the
        # HTTP 1.1 spec.
        elif http_method.upper() in ('GET', 'HEAD') and has_params:
            raise ValueError('GET/HEAD requests should not include body.')

        # generate the basic OAuth parameters
        request.oauth_params = self.get_oauth_params(request)

        # generate the signature
        request.oauth_params.append(('oauth_signature', self.get_oauth_signature(request)))

        # render the signed request and return it
        uri, headers, body = self._render(request, formencode=True,
                                          realm=(realm or self.realm))

        if self.decoding:
            log.debug('Encoding URI, headers and body to %s.', self.decoding)
            uri = uri.encode(self.decoding)
            body = body.encode(self.decoding) if body else body
            new_headers = {}
            for k, v in headers.items():
                new_headers[k.encode(self.decoding)] = v.encode(self.decoding)
            headers = new_headers
        return uri, headers, body
