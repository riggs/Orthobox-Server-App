# -*- coding: utf-8 -*-
"""
Cornice services.
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import json
from cornice import Service
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from orthobox.data_store import (get_upload_token, store_result_data, delete_session_credentials, get_session_params,
                                 get_oauth_creds, get_result_data, get_metadata, new_oauth_creds, store_result)
from orthobox.evaluation import evaluate, _select_criteria, get_moodle_grade, _get_box_name
from orthobox.tool_provider import WebObToolProvider


results = Service(name='demo', path='/results/{session_id}', description="SimPortal results")
configure = Service(name='configure', path='/configure/{version_string}', description="SimPortal demo evaluation parameters")
jnlp = Service(name='jnlp', path='/jnlp/{session_id}.jnlp', description='Generated jnlp file for session')
jar = Service(name='jar', path='/jar/orthobox-signed.jar')  # This can go away if/when python is running under apache

new_oauth = Service(name='new_oauth', path='/new_oauth_creds')


def _parse_json(request):
    try:
        return json.loads(request.body)
    except ValueError:
        raise HTTPBadRequest('Malformed JSON')


@new_oauth.get()
def add_oauth_creds(request):
    """
    Get new OAuth credentials from database
    """
    # TODO: Authentication
    key, secret = new_oauth_creds()
    return {"consumer_key": key, "consumer_secret": secret}


@results.get()
def display_results(request):
    """
    Render template based on evaluated data for session
    """
    # TODO: Limit access to results
    session_id = request.matchdict['session_id']
    try:
        data = get_result_data(session_id)
    except KeyError:
        return HTTPNotFound('Unknown session')
    params = {'duration': data['duration'],
              'error_number': len(data['errors']),
              'pokes': len(data.get('pokes', '')),
              'session_id': session_id}
    params.update(get_metadata(session_id))
    return render_to_response('templates/{0}.pt'.format(params['result']), params, request)


@results.post()
def generate_results(request):
    """
    Set the value.
    """
    # TODO: Ensure the proper box version was run
    session_id = _validate_request(request)

    data = _parse_json(request)
    data['duration'] = int(data['duration']) / 1000
    data['version_string'] = _get_box_name(data['version'])

    result = evaluate(data)

    store_result_data(session_id, data)
    store_result(session_id, result)

    _post_grade(session_id, result)

    delete_session_credentials(session_id)

    return result, data


def _validate_request(request):
    session_id = request.matchdict['session_id']
    try:
        token = get_upload_token(session_id)
    except KeyError:
        raise HTTPNotFound('Unknown session')
    # TODO: Validate token
    return session_id


def _post_grade(session_id, result):
    params = get_session_params(session_id)
    key = params['oauth_consumer_key']
    tool_provider = WebObToolProvider(key, get_oauth_creds(key), params)

    if not tool_provider.is_outcome_service():
        raise HTTPBadRequest("Tool wasn't launched as an outcome service")

    outcome_request = tool_provider.new_request()
    outcome_request.message_identifier = session_id
    outcome_request.post_replace_result(get_moodle_grade(result))

    # TODO: Verify HTTP response for success


@configure.get()
def get_criteria(request):
    """
    Returns the evaluation parameters.
    """
    return _select_criteria(request)


@configure.post()
def set_criteria(request):
    """
    Set the evaluation parameters.
    """
    values = _select_criteria(request)
    data = _parse_json(request)
    for key, value in values.iteritems():
        values[key] = data.get(key, value)
    return values


@jnlp.get()
def generate_jnlp(request):
    params = {}
    params['session_id'] = session_id = request.matchdict['session_id']
    params['url'] = 'http://staging.xlms.org:8128/results/{session_id}'.format(session_id=session_id)
    try:
        params['upload_token'] = get_upload_token(session_id)
    except KeyError:
        raise HTTPNotFound("Unknown session. (Have you already run this activity?)")

    response = render_to_response("templates/jnlp.pt", params, request)
    response.content_type = str('application/x-java-jnlp-file')
    return response


@jar.get()
def serve_jar(request):
    return FileResponse('/var/www/html/orthobox-signed.jar', request=request)
