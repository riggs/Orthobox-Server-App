"""
Evaluation logic and criteria for activities
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'


from pyramid.httpexceptions import HTTPNotFound

_PASS = 'pass'
_FAIL = 'fail'
_INCOMPLETE = 'incomplete'

_POKEY = "pokey_dev"
_PEGGY = "peggy_dev"

_BOX_TYPE = {}
_CRITERIA = {}
_ACTIVITY_NAME = {_PEGGY: "Object Manipulation",
                  _POKEY: "Triangulation"}


def activity_name(version):
    return _ACTIVITY_NAME.get(version, "Unknown Activity")


def evaluate(data):
    # TODO: Audit function logic
    # Will every test have errors & duration?
    box_type = data.get('version')
    if box_type not in _BOX_TYPE: # Unknown box
        return _PASS
    if len(data['errors']) > _CRITERIA[box_type]['errors']:
        result = _FAIL  # value used to retrieve template file
    elif data['duration'] > _CRITERIA[box_type]['timeout']:
        result = _INCOMPLETE
    else:
        result = _BOX_TYPE[box_type](data)
    return result


def _pokey_box(data):
    # Make sure they actually poked stuff
    if len(data['pokes']) >= _CRITERIA[_POKEY]['pokes']:
        result = _PASS
    else:
        result = _INCOMPLETE
    return result


def _peggy_box(data):
    # Don't drop stuff inside of people
    if len(data['drops']) >= _CRITERIA[_PEGGY]['drops']:
        result = _FAIL
    else:
        result = _PASS
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
_CRITERIA[_POKEY] = {'errors': 5, 'timeout': 300, 'pokes': 9}
_CRITERIA[_PEGGY] = {'errors': 5, 'timeout': 300, 'drops': 0}
