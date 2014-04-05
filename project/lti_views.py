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

from .tool_provider import WebObToolProvider
from .data_store import fake_DB, new_id
from .evaluation import activity_name
from .rest_views import _RESULTS, _OAuth_creds


@view_config(route_name='lti')
def lti(request):
    _RESULTS['last_request'] = request
    tool_provider = _authorize_tool_provider(request)
    path = request.matchdict['path']
    if path == 'launch':
        return _launch(request, tool_provider)
    #if path == 'assessment':
    #    return _assessment(request, tool_provider)
    raise HTTPUnauthorized()


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


def _launch(request, tool_provider):
    session = new_id()
    username = tool_provider.username(default="beautiful")
    version = tool_provider.custom_params.get('custom_box_version')
    activity = activity_name(version)
    _RESULTS[session] = {'username': username, 'activity': activity, 'version': version}
    fake_DB[session] = tool_provider
    #fake_DB[tool_provider.tool_consumer_instance_guid]\
    #       [tool_provider.user_id][tool_provider.context_id]\
    #       [tool_provider.resource_link_id][tool_provider.consumer_key] = session
    return render_to_response("templates/demo.pt", locals(), request)


def _assessment(request, tool_provider):
    #if tool_provider.is_outcome_service():
    #    return render_to_response("templates/lti_assessment.pt", locals(),  request)
    if not tool_provider.is_outcome_service():
        raise HTTPBadRequest("Tool wasn't launched as an outcome service")

    outcome_request = tool_provider.new_request()
    outcome_request.message_identifier = uuid4().hex
    outcome_request.post_replace_result(request.POST['score'])

    return Response(str(outcome_request.outcome_response.post_response))
