# -*- coding: utf-8 -*-
"""
LTI services
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from datetime import datetime
from calendar import timegm
from hashlib import sha1

from oauth2 import Error as OAuthError
from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPUnauthorized

from orthobox.tool_provider import WebObToolProvider
from orthobox.rest_views import _url_params
from orthobox.data_store import (get_upload_token, verify_resource_oauth, authorize_user, store_session_params,
                                 get_oauth_creds, activity_display_name, log)


@view_config(route_name='lti_launch')
def lti_launch(request):
    tool_provider = _authorize_tool_provider(request)
    try:
        session_id = _new_session(tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)
    params = _url_params(session_id)
    params['session_id'] = session_id
    params['username'] = tool_provider.username(default="lovely")
    params['activity'] = activity_display_name(tool_provider.custom_params.get('custom_box_version'))
    params['upload_token'] = get_upload_token(session_id)
    return render_to_response("templates/begin.pt", params, request)


@view_config(route_name='lti_progress')
def lti_progress(request):
    tool_provider = _authorize_tool_provider(request)
    return render_to_response("templates/triangulation.pt", {}, request)


def _new_session(tool_provider):
    """
    Generate new session data
    """
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id
    moodle_uid = _hash(instance_id, user_id)
    moodle_resource_id = _hash(instance_id, resource_id)

    # Verify OAuth creds for this resource
    try:
        verify_resource_oauth(moodle_resource_id, tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    try:
        session_id = authorize_user(moodle_uid, tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    store_session_params(session_id, params=tool_provider.params)

    return session_id


def _authorize_tool_provider(request):
    """
    Create and validate WebObToolProvider from request.
    """
    params = request.POST.mixed()

    key = params.get('oauth_consumer_key')
    if key is None:
        log.debug('HTTPUnauthorized: ' + str(params))
        raise HTTPUnauthorized("Missing OAuth data. Params:\r\n{0}".format(str(params)))

    secret = get_oauth_creds(key)
    if secret is None:
        log.debug('HTTPUnauthorized: ' + str(params))
        raise HTTPUnauthorized("Invalid OAuth consumer key")

    tool_provider = WebObToolProvider(key, secret, params)

    try:
        tool_provider.valid_request(request)
    except OAuthError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    now = timegm(datetime.utcnow().utctimetuple())
    if now - int(tool_provider.oauth_timestamp) > 60 * 60:
        log.debug('HTTPUnauthorized: OAuth timeout')
        raise HTTPUnauthorized("OAuth timeout")

    _validate_nonce(tool_provider.oauth_nonce, now)

    return tool_provider


_OAuth_creds = {}
def _validate_nonce(nonce, now):
    timestamp = _OAuth_creds.get(nonce)
    if timestamp is None:
        _OAuth_creds[nonce] = now
    elif now - timestamp > 60 * 60:
        log.debug('HTTPUnauthorized: OAuth nonce timeout')
        raise HTTPUnauthorized("OAuth nonce timeout")


def _hash(*args):
    h = sha1()
    for item in args:
        h.update(item)
    return h.hexdigest()
