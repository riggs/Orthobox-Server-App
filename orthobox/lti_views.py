# -*- coding: utf-8 -*-
"""
LTI services
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from collections import namedtuple
from datetime import datetime
from calendar import timegm
from hashlib import sha1

from oauth2 import Error as OAuthError
from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPUnauthorized

from orthobox.tool_provider import WebObToolProvider
from orthobox.rest_views import _url_params
from orthobox.evaluation import get_progress_count
from orthobox.data_store import (get_upload_token, verify_resource_oauth, authorize_user, store_session_params,
                                 get_oauth_creds, activity_display_name, log, get_session_data, get_metadata, _PASS,
                                 get_user_data_by_uid, get_ids_from_moodle_uid, get_user_data_by_context_id)


@view_config(route_name='lti_launch')
def lti_launch(request):
    log.debug(request.body)
    tool_provider = _authorize_tool_provider(request)

    try:
        session_id = _new_session(tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    params = _url_params(session_id)
    params['session_id'] = session_id
    params['username'] = tool_provider.username(default="lovely")
    params['activity'] = activity_display_name(tool_provider.get_custom_param('box_version'))
    params['upload_token'] = get_upload_token(session_id)
    return render_to_response("templates/begin.pt", params, request)


@view_config(route_name='lti_progress')
def lti_progress(request):
    tool_provider = _authorize_tool_provider(request)

    instance_id = tool_provider.tool_consumer_instance_guid
    moodle_uid = _hash(instance_id, 'user_id=' + tool_provider.user_id)
    moodle_resource_id = _hash(instance_id, 'resource_link_id=' + tool_provider.resource_link_id)
    context_id = _hash(instance_id, 'context_id=' + tool_provider.context_id)
    activity = tool_provider.get_custom_param('box_version')

    # Verify OAuth creds for this resource
    try:
        verify_resource_oauth(moodle_resource_id, tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    params = list()
    MoodleID = namedtuple('MoodleID', 'uid, username')
    if 'Instructor' in tool_provider.roles:
        users = get_user_data_by_context_id(context_id)
        for uid, user_data in users.items():
            moodle_id = MoodleID(**get_ids_from_moodle_uid(user_data['moodle_uid']))
            params.append(_gather_template_data(moodle_id, user_data[activity], activity))
    else:
        moodle_id = MoodleID(**get_ids_from_moodle_uid(moodle_uid))
        activity_data = get_user_data_by_uid(moodle_id.uid, context_id)[activity]
        params.append(_gather_template_data(moodle_id, activity_data, activity))
    return render_to_response("templates/progress.pt", {'params': params}, request)


def _gather_template_data(moodle_id, activity_data, activity):
    not_passing, passing, all_errors, drops, hover_data = _build_graph_data(activity_data['sessions'])
    activity_name = activity_display_name(activity)
    return {'uid': moodle_id.uid,
            'not_passing': not_passing,
            'passing': passing,
            'all_errors': all_errors,
            'drops': drops,
            'hover_data': hover_data,
            'username': moodle_id.username,
            'activity': activity_name,
            'activity_string': activity,
            'attempts': len(not_passing) + len(passing),
            'completion': '{0} of {1}'.format(*get_progress_count(activity_data['grade']))}


def _build_graph_data(session_ids):
    passing = list()
    not_passing = list()
    all_errors = list()  # each element: [trial #, end time, start time]
    drops = list()
    # [number of errors for not_passing, # of errors for passing, error length, drop time]
    hover_data = [list(), list(), list(), list()]
    for i, session_id in enumerate(session_ids):
        i += 1  # 1-indexed for display purposes. PS: Namespaces rock

        data = get_session_data(session_id)
        if not data:
            continue

        error_count = 0
        for error in data['errors']:
            end = error['endtime']
            duration = error['duration']
            all_errors.append([i, end / 1000, (end - duration) / 1000])
            hover_data[2].append(duration / 1000)
            error_count += 1

        for drop in data.get('drops', []):
            drop_time = drop['endtime'] / 1000
            drops.append([i, drop_time])
            hover_data[3].append(drop_time)

        metadata = get_metadata(session_id)
        if metadata['result'] == _PASS:
            passing.append([i, data['duration']])
            hover_data[1].append(error_count)
        else:
            not_passing.append([i, data['duration']])
            hover_data[0].append(error_count)

    return not_passing, passing, all_errors, drops, hover_data


def _new_session(tool_provider):
    """
    Generate new session data
    """
    instance_id = tool_provider.tool_consumer_instance_guid
    moodle_uid = _hash(instance_id, 'user_id=' + tool_provider.user_id)
    moodle_resource_id = _hash(instance_id, 'resource_link_id=' + tool_provider.resource_link_id)
    context_id = _hash(instance_id, 'context_id=' + tool_provider.context_id)

    # Verify OAuth creds for this resource
    try:
        verify_resource_oauth(moodle_resource_id, tool_provider)
    except AssertionError as e:
        log.debug('HTTPUnauthorized: ' + e.message)
        raise HTTPUnauthorized(e.message)

    try:
        session_id = authorize_user(moodle_uid, context_id, tool_provider)
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
