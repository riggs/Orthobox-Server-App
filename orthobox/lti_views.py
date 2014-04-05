# -*- coding: utf-8 -*-
"""
LTI services
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'

from datetime import datetime
from calendar import timegm
from uuid import uuid4

from oauth2 import Error as OAuthError

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest, HTTPUnauthorized

from orthobox.tool_provider import WebObToolProvider
from orthobox.data_store import fake_DB, new_session
from orthobox.evaluation import activity_name
from orthobox.rest_views import _RESULTS, _OAuth_creds


@view_config(route_name='lti_launch')
def lti_launch(request):
    _RESULTS['last_request'] = request
    tool_provider = _authorize_tool_provider(request)
    session = new_session(tool_provider)
    username = tool_provider.username(default="beautiful")
    version = tool_provider.custom_params.get('custom_box_version')
    activity = activity_name(version)
    _RESULTS[session] = {'username': username, 'activity': activity, 'version': version}
    fake_DB[session] = tool_provider
    return render_to_response("templates/demo.pt", locals(), request)


def _authorize_tool_provider(request):
    """
    Create and validate WebObToolProvider from request.
    """
    params = request.POST.mixed()

    key = params.get('oauth_consumer_key')
    if key is None:
        raise HTTPBadRequest("Missing OAuth data. Params:\r\n{0}".format(str(params)))

    secret = _OAuth_creds.get(key)
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

    timestamp = _OAuth_creds.get(tool_provider.oauth_nonce)
    if timestamp is None:
        _OAuth_creds[tool_provider.oauth_nonce] = now
    elif now - timestamp > 60 * 60:
        raise HTTPBadRequest("OAuth nonce timeout")

    return tool_provider

