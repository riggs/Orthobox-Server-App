"""
LTI services
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'

from datetime import datetime
from calendar import timegm

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest

from .tool_provider import WebObToolProvider


_OAuth_creds = {u"consumer_key": u"shared_secret"}


@view_config(route_name='lti_root')
def lti_root(request):
    return render_to_response("templates/lti_root.pt", {}, request)


@view_config(route_name='lti')
def lti(request):
    path = request.matchdict['path']
    if path == 'launch':
        return _launch(request)
    return Response("Da fuq you goin?")


def _launch(request):
    return Response(str(request), 200)
    params = request.POST.mixed()

    key = params.get('oauth_consumer_key')
    if key is None:
        raise HTTPBadRequest("Missing OAuth data. Params:\r\n{0}".format(str(params)))

    secret = _OAuth_creds.get(key)
    if secret is None:
        raise HTTPBadRequest("Invalid OAuth consumer key")

    tool_provider = WebObToolProvider(key, secret, params)

    if not tool_provider.valid_request(request):
        raise HTTPBadRequest("Invalid OAuth signature")

    now = timegm(datetime.utcnow().utctimetuple())
    if now - tool_provider.oauth_timestamp > 60 * 60:
        raise HTTPBadRequest("Request timed out")

    timestamp = _OAuth_creds.get(tool_provider.oauth_nonce)
    if timestamp is None:
        _OAuth_creds[tool_provider.oauth_nonce] = now
    elif now - timestamp > 60 * 60:
        raise HTTPBadRequest("OAuth nonce timeout")

    return Response("OAuth succeeded")