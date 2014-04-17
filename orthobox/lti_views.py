# -*- coding: utf-8 -*-
"""
LTI services
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from datetime import datetime
from calendar import timegm

from oauth2 import Error as OAuthError

from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest

from orthobox.tool_provider import WebObToolProvider
from orthobox.data_store import new_session, get_oauth_creds, get_upload_token
from orthobox.evaluation import activity_name
from orthobox.rest_views import _url_params


@view_config(route_name='lti_launch')
def lti_launch(request):
    tool_provider = _authorize_tool_provider(request)
    session_id = new_session(tool_provider)
    params = _url_params(session_id)
    params['session_id'] = session_id
    params['username'] = tool_provider.username(default="lovely")
    params['activity'] = activity_name(tool_provider.custom_params.get('custom_box_version'))
    params['upload_token'] = get_upload_token(session_id)
    return render_to_response("templates/begin.pt", params, request)


def _authorize_tool_provider(request):
    """
    Create and validate WebObToolProvider from request.
    """
    params = request.POST.mixed()

    key = params.get('oauth_consumer_key')
    if key is None:
        raise HTTPBadRequest("Missing OAuth data. Params:\r\n{0}".format(str(params)))

    secret = get_oauth_creds(key)
    if secret is None:
        raise HTTPBadRequest("Invalid OAuth consumer key")

    tool_provider = WebObToolProvider(key, secret, params)

    try:
        tool_provider.valid_request(request)
    except OAuthError as e:
        raise HTTPBadRequest(e.message)

    now = timegm(datetime.utcnow().utctimetuple())
    if now - int(tool_provider.oauth_timestamp) > 60 * 60:
        raise HTTPBadRequest("Request timed out")

    _validate_nonce(tool_provider.oauth_nonce, now)

    return tool_provider

_OAuth_creds = {}
def _validate_nonce(nonce, now):
    timestamp = _OAuth_creds.get(nonce)
    if timestamp is None:
        _OAuth_creds[nonce] = now
    elif now - timestamp > 60 * 60:
        raise HTTPBadRequest("OAuth nonce timeout")
