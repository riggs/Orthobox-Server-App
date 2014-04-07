# -*- coding: utf-8 -*-
"""
Evaluation logic and criteria for activities
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from pyramid.httpexceptions import HTTPNotFound


_PASS = 'pass'
_FAIL = 'fail'
_INCOMPLETE = 'incomplete'

_POKEY = 'pokey'
_PEGGY = 'peggy'

_BOX_STRING = {1: _POKEY, 2: _PEGGY}

_BOX_FUNCTION = {}
_CRITERIA = {}

_ACTIVITY_NAME = {_PEGGY: "Object Manipulation",
                  _POKEY: "Triangulation"}

_GRADES = {"pass": 1.0, "fail": 0.0, "incomplete": 0.5}

# TODO: Session specific evaluation criteria
_CRITERIA[_POKEY] = {'errors': 5, 'timeout': 300, 'pokes': 9}
_CRITERIA[_PEGGY] = {'errors': 5, 'timeout': 300, 'drops': 0}


def activity_name(version_string):
    return _ACTIVITY_NAME.get(version_string, "Unknown Activity")


def evaluate(data):
    # TODO: Audit function logic
    # Will every test have errors & duration?
    box_type = data.get('version_string')
    if box_type not in _BOX_FUNCTION:   # Unknown box
        return _PASS
    if len(data['errors']) > _CRITERIA[box_type]['errors']:
        result = _FAIL  # value used to retrieve template file
    elif data['duration'] > _CRITERIA[box_type]['timeout']:
        result = _INCOMPLETE
    else:
        result = _BOX_FUNCTION[box_type](data)
    return result


def get_moodle_grade(result):
    return str(_GRADES[result])


def _pokey_box(data):
    # Make sure they actually poked stuff
    if len(data['pokes']) >= _CRITERIA[_POKEY]['pokes']:
        result = _PASS
    else:
        result = _INCOMPLETE
    return result

_BOX_FUNCTION[_POKEY] = _pokey_box


def _peggy_box(data):
    # Don't drop stuff inside of people
    if len(data['drops']) >= _CRITERIA[_PEGGY]['drops']:
        result = _FAIL
    else:
        result = _PASS
    return result

_BOX_FUNCTION[_PEGGY] = _peggy_box


def _select_criteria(request):
    key = request.matchdict['version_string']
    value = _CRITERIA.get(key)
    if value is None:
        raise HTTPNotFound('Unknown hardware version')
    return value


def _get_box_name(version):
    return _BOX_STRING(version)
