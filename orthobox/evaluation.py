# -*- coding: utf-8 -*-
"""
Evaluation logic and criteria for activities
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from pyramid.httpexceptions import HTTPNotFound

from orthobox.data_store import (_POKEY, _PEGGY, _PASS, _FAIL, _INCOMPLETE, get_ids_for_session, get_grade, store_grade)


_ERROR_CUTOFF = 250

_REQUIRED_SUCCESSES = 3

_BOX_FUNCTION = {}

# TODO: Session specific evaluation criteria
_CRITERIA = {
    _POKEY: {'errors': 10, 'timeout': 300, 'pokes': 9},
    _PEGGY: {'errors': 10, 'timeout': 300, 'drops': 1}
}


def evaluate(session_id, data):
    # TODO: Audit evaluation logic
    # Will every test have errors & duration?
    box_type = data.get('version_string')
    errors = [error for error in data.get('errors', []) if error['len'] >= _ERROR_CUTOFF]
    duration = data['duration']
    if len(errors) > _CRITERIA[box_type]['errors']:
        result = _FAIL
    elif duration > _CRITERIA[box_type]['timeout']:
        result = _INCOMPLETE
    else:
        result = _BOX_FUNCTION[box_type](data)

    uid, context_id = get_ids_for_session(session_id)
    if result is _PASS:     # Add completion credit to grade
        grade = get_grade(uid, context_id, box_type)
        grade += 1 / _REQUIRED_SUCCESSES
    else:
        grade = 0
    store_grade(uid, context_id, box_type, grade)

    return result, grade


def get_progress_count(grade):
    """
    Returns number of consecutive successes, number of required consecutive successes.
    """
    return int(round(grade * _REQUIRED_SUCCESSES)), _REQUIRED_SUCCESSES


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
