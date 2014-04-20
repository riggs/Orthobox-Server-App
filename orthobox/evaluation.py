# -*- coding: utf-8 -*-
"""
Evaluation logic and criteria for activities
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from pyramid.httpexceptions import HTTPNotFound

from orthobox.data_store import (_POKEY, _PEGGY, _PASS, _FAIL, _INCOMPLETE, get_uid_for_session, get_grade, store_grade)


_REQUIRED_SUCCESSES = 3

_BOX_FUNCTION = {}
_CRITERIA = {}

# TODO: Session specific evaluation criteria
_CRITERIA[_POKEY] = {'errors': 5, 'timeout': 300, 'pokes': 9}
_CRITERIA[_PEGGY] = {'errors': 5, 'timeout': 300, 'drops': 0}


def evaluate(session_id, data):
    # TODO: Audit evaluation logic
    # Will every test have errors & duration?
    box_type = data.get('version_string')
    errors = data.get('errors', [])
    duration = data['duration']
    if len(errors) > _CRITERIA[box_type]['errors']:
        result = _FAIL
    elif duration > _CRITERIA[box_type]['timeout']:
        result = _INCOMPLETE
    else:
        result = _BOX_FUNCTION[box_type](data)

    uid = get_uid_for_session(session_id)
    if result is _PASS:     # Add completion credit to grade
        grade = get_grade(uid, box_type)
        grade += 1 / _REQUIRED_SUCCESSES
    else:
        grade = 0
    store_grade(uid, box_type, grade)

    return result, grade


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


def _select_criteria(version):
    value = _CRITERIA.get(version)
    if value is None:
        raise HTTPNotFound('Unknown hardware version')
    return value
