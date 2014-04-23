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

from orthobox.data_store import (get_upload_token, store_activity_data, delete_session_credentials, get_session_params,
                                 get_oauth_creds, get_result_data, get_metadata, new_oauth_creds, store_result,
                                 dump_session_data, get_box_name, log)
from orthobox.evaluation import evaluate, _select_criteria, get_progress_count, _ERROR_CUTOFF
from orthobox.tool_provider import WebObToolProvider


_BASE_URL = "http://staging.xlms.org"
_CSS_PATH = "/pfi.css"
_RESULTS_PATH = '/{session_id}/results'
_WAITING_PATH = '/{session_id}/view_results'
_JNLP_PATH = '/{session_id}/launch.jnlp'

results = Service(name='results', path=_RESULTS_PATH)
view_results = Service(name='view_results', path=_WAITING_PATH)
jnlp = Service(name='jnlp', path=_JNLP_PATH, description='Generated jnlp file for session')
configure = Service(name='configure', path='/configure/{version_string}',
                    description="SimPortal demo evaluation parameters")
jar = Service(name='jar', path='/orthobox-signed.jar')  # FIXME: Irrelevant under apache

# TODO: Some sort of security to limit credential generation
new_oauth = Service(name='new_oauth', path='/new_oauth_creds')

session_data = Service(name='session_data', path='/session_data')


def _parse_json(request):
    try:
        return json.loads(request.body)
    except ValueError:
        log.debug('HTTPBadRequest: Malformed JSON')
        raise HTTPBadRequest('Malformed JSON')


def _url_params(session_id):
    _PORT = ':8128'  # FIXME: Irrelevant under apache

    return {'css_url': ''.join([_BASE_URL, _CSS_PATH]),
            'jnlp_url': _PORT.join([_BASE_URL, _JNLP_PATH]).format(session_id=session_id),
            'waiting_url': _PORT.join([_BASE_URL, _WAITING_PATH]).format(session_id=session_id),
            'results_url': _PORT.join([_BASE_URL, _RESULTS_PATH]).format(session_id=session_id),
            'relaunch_url': '/launch'}


@session_data.get()
def return_session_data(request):
    return dump_session_data()


@view_results.get()
def waiting_page(request):
    """
    Display page while waiting for session to proceed.
    """
    session_id = request.matchdict['session_id']
    params = _url_params(session_id)
    params.update(get_metadata(session_id))
    return render_to_response("templates/view_results.pt", params, request)


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
        log.debug('HTTPNotFound: Unknown session ' + session_id)
        raise HTTPNotFound('Unknown session')
    params = _url_params(session_id)
    params.update({'duration': data['duration'],
                   'error_number': len([error for error in data['errors'] if error['len'] >= _ERROR_CUTOFF]),
                   'pokes': len(data.get('pokes', '')),
                   'session_id': session_id})
    params.update(get_metadata(session_id))
    params['completion'] = "{0} of {1}".format(*get_progress_count(params['grade']))
    return render_to_response('templates/{0}.pt'.format(params['result']), params, request)


@results.post()
def generate_results(request):
    """
    Set the value.
    """
    # TODO: Ensure the proper box version was run
    session_id = _validate_request(request)

    data = _parse_json(request)
    data['duration'] = int(data['duration']) // 1000
    data['version_string'] = get_box_name(data['version'])

    result, grade = evaluate(session_id, data)

    store_activity_data(session_id, data)
    store_result(session_id, result, grade)

    _post_grade(session_id, grade)

    delete_session_credentials(session_id)

    return result, data


def _validate_request(request):
    session_id = request.matchdict['session_id']
    try:
        token = get_upload_token(session_id)
    except KeyError:
        log.debug('HTTPNotFound: Unknown session %s', session_id)
        raise HTTPNotFound('Unknown session')
    # TODO: Validate token
    assert token
    return session_id


def _post_grade(session_id, grade):
    params = get_session_params(session_id)
    key = params['oauth_consumer_key']
    tool_provider = WebObToolProvider(key, get_oauth_creds(key), params)

    if not tool_provider.is_outcome_service():
        log.debug('HTTPBadRequest: Not launched as outcome service')
        raise HTTPBadRequest("Tool wasn't launched as an outcome service")

    outcome_request = tool_provider.new_request()
    outcome_request.message_identifier = session_id
    log.debug(outcome_request.generate_request_xml())
    outcome_response = outcome_request.post_replace_result(round(grade, 2))    # Round to 2 digits for moodle

    # TODO: Verify HTTP response for success

    return outcome_response


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
    session_id = request.matchdict['session_id']
    params = _url_params(session_id)
    params['session_id'] = session_id
    try:
        params['upload_token'] = get_upload_token(session_id)
    except KeyError:
        log.debug('HTTPNotFound: Unknown session (already run?)' + session_id)
        raise HTTPNotFound("Unknown session. (Have you already run this activity?)")

    response = render_to_response("templates/jnlp.pt", params, request)
    response.content_type = str('application/x-java-jnlp-file')
    return response


@jar.get()
def serve_jar(request):
    return FileResponse('/var/www/html/orthobox-signed.jar', request=request)
