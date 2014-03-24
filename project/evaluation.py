"""
Evaluation logic and criteria for activities
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'


from pyramid.httpexceptions import HTTPNotFound


_POKEY = "pokey_dev"
_PEGGY = "peggy_dev"

_BOX_TYPE = {}
_CRITERIA = {}
_ACTIVITY_NAME = {_PEGGY: "Object Manipulation",
                  _POKEY: "Triangulation"}


def activity_name(version):
    return _ACTIVITY_NAME.get(version, "Unknown Activity")


def _pass(*_):
    """placeholder function.
    """
    return "pass"


def evaluate(data):
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


def _peggy_box(data):
    # TODO: determine evaluation criteria
    result = _pass(data)
    return result


def _select_criteria(request):
    key = request.matchdict['version']
    value = _CRITERIA.get(key)
    if value is None:
        raise HTTPNotFound('Unknown hardware version')
    return value


_BOX_TYPE[_POKEY] = _pokey_box
_BOX_TYPE[_PEGGY] = _peggy_box

# TODO: Session specific evaluation criteria
_CRITERIA[_POKEY] = {'errors': 5, 'timeout': 300, 'pokes': 10}
_CRITERIA[_PEGGY] = {'errors': 5, 'timeout': 300}
