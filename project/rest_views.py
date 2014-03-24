"""
Cornice services.
"""

from __future__ import division, absolute_import, print_function


import json
from cornice import Service
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import Response

from .evaluation import evaluate, _select_criteria
from .data_store import fake_DB


demo = Service(name='demo', path='/demo/{session}',
               description="SimPortal demo")
criteria = Service(name='criteria', path='/criteria/{version}',
                   description="SimPortal demo evaluation parameters")
jnlp = Service(name='jnlp', path='/jnlp/{uid}.jnlp', description='Generated jnlp file for session')


def _parse_json(request):
    try:
        return json.loads(request.body)
    except ValueError:
        raise HTTPBadRequest('Malformed JSON')


_RESULTS = {}


@demo.get()
def display_results(request):
    key = request.matchdict['session']
    value = _RESULTS.get(key)
    if value is None:
        return HTTPNotFound('Unknown session')
    result, data = value
    return render_to_response('templates/{0}.pt'.format(result),
                              {'duration': data['duration'],
                               'error_number': len(data['errors'])},
                              request)


@demo.post()
def generate_results(request):
    """Set the value.
    """
    key = request.matchdict['session']
    data = _parse_json(request)
    data['duration'] /= 1000
    result = evaluate(data)
    _RESULTS[key] = (result, data)
    return result, data


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
    return Response("Working on it")
    uid = request.matchdict['uid']
    session = hash(fake_DB[uid])
    response = render_to_response("template/jnlp.pt", locals(), request)
    #response.content_type = 'application/x-java-jnlp-file'
    return response
