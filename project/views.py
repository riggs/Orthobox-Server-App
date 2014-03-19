""" Cornice services.
"""
import json
from cornice import Service

from pyramid.renderers import render_to_response

demo = Service(name='demo', path='/demo/{value}',
                 description="SimPortal demo")
eval = Service(name='eval', path='/eval_config',
                 description="SimPortal demo evaluation parameters")

_VALUES = {}
_EVAL = {'errors': 5, 'timeout': 300}


@demo.get()
def display_results(request):
    key = request.matchdict['value']
    value = _VALUES.get(key)
    if value is None:
        return
    result, payload = value
    return render_to_response('templates/{0}.pt'.format(result),
                              {'duration': payload['duration'],
                               'error_number': len(payload['errors'])},
                              request)


@demo.post()
def set_value(request):
    """Set the value.
    """
    key = request.matchdict['value']
    try:
        payload = json.loads(request.body)
    except ValueError:
        return False
    payload['duration'] = payload['duration'] // 1000
    if (not len(payload['touches'])) or len(payload['errors']) > _EVAL['errors']:
        result = "fail"
    elif  payload['duration'] > _EVAL['timeout']:
        result = "incomplete"
    else:
        result = "pass"
    _VALUES[key] = (result, payload)
    return result, payload


@eval.get()
def get_eval(request):
    """Returns the evaluation parameters.
    """
    return _EVAL


@eval.post()
def set_eval(request):
    """Set the evaluation parameters.
    """
    try:
        payload = json.loads(request.body)
    except ValueError:
        return False
    _EVAL['errors'] = payload.get('errors', _EVAL['errors'])
    _EVAL['timeout'] = payload.get('timeout', _EVAL['timeout'])
    return _EVAL   
