""" Cornice services.
"""

from __future__ import division

import json
from cornice import Service

from pyramid.renderers import render_to_response

demo = Service(name='demo', path='/demo/{value}',
               description="SimPortal demo")
criteria = Service(name='criteria', path='/eval_config',
                   description="SimPortal demo evaluation parameters")

_VALUES = {}
# TODO: Context-based eval criteria
_EVAL = {'errors': 5, 'timeout': 300, 'pokes': 10}
_BOX_TYPE = {}


def _pass(*_):
    """placeholder function.
    """
    return "pass"


@demo.get()
def display_results(request):
    key = request.matchdict['value']
    value = _VALUES.get(key)
    if value is None:
        return
    result, data = value
    return render_to_response('templates/{0}.pt'.format(result),
                              {'duration': data['duration'],
                               'error_number': len(data['errors'])},
                              request)


@demo.post()
def set_value(request):
    """Set the value.
    """
    key = request.matchdict['value']
    try:
        data = json.loads(request.body)
    except ValueError:
        return "Failed to parse JSON"
    data['duration'] /= 1000
    result = _eval(data)
    _VALUES[key] = (result, data)
    return result, data


def _eval(data):
    # TODO: Audit function logic
    # Will every test have errors & duration?
    if len(data['errors']) > _EVAL['errors']:
        result = "fail"  # value used to retrieve template file
    elif data['duration'] > _EVAL['timeout']:
        result = "incomplete"
    else:
        # Should the test pass if the device isn't recognized?
        result = _BOX_TYPE.get(data['version'], _pass)(data)
    return result


def _pokey_box(data):
    # Make sure they actually poked stuff
    if len(data['pokes']):
        result = "pass"
    else:
        result = "fail"
    return result


_BOX_TYPE['pokey_dev'] = _pokey_box


def _peggy_box(data):
    # TODO: determine evaluation criteria
    result = _pass(data)
    return result


_BOX_TYPE['peggy_dev'] = _peggy_box


@criteria.get()
def get_eval(request):
    """Returns the evaluation parameters.
    """
    return _EVAL


@criteria.post()
def set_eval(request):
    """Set the evaluation parameters.
    """
    try:
        data = json.loads(request.body)
    except ValueError:
        return False
    for key, value in _EVAL.iteritems():
        _EVAL[key] = data.get(key, value)
    return _EVAL   
