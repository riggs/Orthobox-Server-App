"""
Cornice services.
"""

from __future__ import division, absolute_import, print_function


import json
from cornice import Service
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse

from .evaluation import evaluate, _select_criteria
from .data_store import fake_DB
from .tool_provider import WebObToolProvider
from .lti_views import _OAuth_creds


_RESULTS = {}

demo = Service(name='demo', path='/demo/{session}',
               description="SimPortal demo")
criteria = Service(name='criteria', path='/criteria/{version}',
                   description="SimPortal demo evaluation parameters")
jnlp = Service(name='jnlp', path='/jnlp/{session}.jnlp', description='Generated jnlp file for session')
jar = Service(name='jar', path='/jar/orthobox.jar')

last_request = Service(name='last_request', path='/last_request',
                       description="last_request")


def _parse_json(request):
    try:
        return json.loads(request.body)
    except ValueError:
        raise HTTPBadRequest('Malformed JSON')


@last_request.get()
def echo_request(request):
    return str(_RESULTS['last_request'])


@demo.get()
def display_results(request):
    session = request.matchdict['session']
    value = _RESULTS.get(session)
    if value is None:
        return HTTPNotFound('Unknown session')
    result, data = value
    params = {'duration': data['duration'],
              'error_number': len(data['errors']),
              'activity': _RESULTS['activity'],
              'username': _RESULTS['username'],
              'pokes': data.get('pokes'),
              'session': session}
    return render_to_response('templates/{0}.pt'.format(result), params, request)


@demo.post()
def generate_results(request):
    """Set the value.
    """
    session = request.matchdict['session']
    data = _parse_json(request)
    data['duration'] /= 1000
    result = evaluate(data)
    _RESULTS[session] = (result, data)

    _post_grade(session, result)

    return result, data


def _post_grade(session, result):
    return
    tool_provider = fake_DB[session]
    key = tool_provider.oauth_consumer_key
    tool_provider = WebObToolProvider(key, _OAuth_creds[key], tool_provider.params)

    if not tool_provider.is_outcome_service():
        raise HTTPBadRequest("Tool wasn't launched as an outcome service")

    outcome_request = tool_provider.new_request()
    outcome_request.message_identifier = session
    outcome_request.post_replace_result(request.POST['score'])


@criteria.get()
def get_criteria(request):
    """Returns the evaluation parameters.
    """
    return _select_criteria(request)


@criteria.post()
def set_criteria(request):
    """Set the evaluation parameters.
    """
    values = _select_criteria(request)
    data = _parse_json(request)
    for key, value in values.iteritems():
        values[key] = data.get(key, value)
    return values


@jnlp.get()
def generate_jnlp(request):
    session = request.matchdict['session']
    url = 'http://staging.xlms.org:8128/demo/{session}'.format(session=session)
    response = render_to_response("templates/jnlp.pt", {'url': url, 'session': session}, request)
    response.content_type = 'application/x-java-jnlp-file'
    return response


@jar.get()
def serve_jar(request):
    return FileResponse('/var/www/html/orthobox.jar', request=request)
