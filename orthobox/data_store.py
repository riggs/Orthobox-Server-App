# -*- coding: utf-8 -*-
"""
Use lmdb as backend.

Database schema:

1 lmdb environment, 7 databases: sessions, data, metadata, users, moodle, oauth, unregistered_oauth
DB keys: utf-8 encoded text
DB values: utf-8 encoded JSON

uid = uuid4().hex
session_id = uuid4().hex

instance_id = tool_provider.tool_consumer_instance_guid
moodle_uid = hashlib.sha1(instance_id + tool_provider.user_id).hexdigest()
moodle_resource_id = hashlib.sha1(instance_id + tool_provider.resource_link_id).hexdigest()
context_id = hashlib.sha1(instance_id + tool_provider.context_id)

sessions = {
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
}
Note: Remove after successful use

data = {   # 'Sanitized' copy to be kept for later analysis.
    session_id: {'uid': uid,
                 'video_url': <identifier (URL) for video>,
                 'data': <JSON received: 'raw_errors': the raw data,
                                         'errors': raw_errors normalized with > 250ms length>}
}

metadata = {
    session_id: {'uid': uid,
                 'context': context_id,
                 'activity': <activity display name>,
                 'video_url': <identifier (URL) for video>,
                 'result': <pass/fail/incomplete status>,
                 'grade': <completion percentage after session, eg. 0%, 33%, 66%, 100%>,
                 'version_string': <activity version string>,
                 'return_url': <lti spec 'launch_presentation_return_url'>}
}

users = {
    context_id: {uid: {'moodle_uid': moodle_uid,
                       'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>},
                       'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>}}}
}

moodle = {
    moodle_uid: {'uid': uid, 'username': username}
    moodle_resource_id: {'consumer_key': <OAuth consumer key>, 'consumer_secret': <OAuth shared secret>}
}

oauth = {
    oauth_consumer_key: oauth_consumer_secret
}

unregistered_oauth = {
    oauth_consumer_key: oauth_consumer_secret
}
Note: Keys are created in unregistered, then moved to oauth once associated with moodle_resource_id
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import lmdb
import json
import logging

from os import environ
from uuid import uuid4

from orthobox.lmdb_wrapper import LMDB_Dict

log = logging.getLogger('orthobox')

_10_GB = 10737418240  # Size of address-space for mmap, largest capacity for environment, not a memory requirement.

_LMDB_DATADIR = environ.get('LMDB_DATADIR', 'lmdb_data')
_LMDB_ENV = lmdb.open(_LMDB_DATADIR, map_size=_10_GB, max_dbs=7)

_SESSIONS_DB = LMDB_Dict(_LMDB_ENV, 'sessions')
_DATA_DB = LMDB_Dict(_LMDB_ENV, 'data')
_USERS_DB = LMDB_Dict(_LMDB_ENV, 'users')
_METADATA_DB = LMDB_Dict(_LMDB_ENV, 'metadata')
_MOODLE_DB = LMDB_Dict(_LMDB_ENV, 'moodle')
_OAUTH_DB = LMDB_Dict(_LMDB_ENV, 'oauth')
_UNREGISTERED_OAUTH = LMDB_Dict(_LMDB_ENV, 'unregistered_oauth')

_DATABASES = (_SESSIONS_DB, _DATA_DB, _USERS_DB, _METADATA_DB, _MOODLE_DB, _UNREGISTERED_OAUTH, _OAUTH_DB)

_VIDEO_URL = "https://s3.amazonaws.com/orthoboxes-video/{session_id}.mp4"

# The evaluation strings below are used to determine template file name to be served.
_PASS = 'pass'
_FAIL = 'fail'
_INCOMPLETE = 'incomplete'

_POKEY = 'pokey'
_PEGGY = 'peggy'

_BOX_VERSION = {1: _POKEY, 2: _PEGGY}

_ACTIVITY_NAME = {_PEGGY: "Object Manipulation",
                  _POKEY: "Triangulation"}


def new_oauth_creds():
    # TODO: Authentication so this can be run automatically
    key = uuid4().hex
    secret = uuid4().hex
    _UNREGISTERED_OAUTH[key] = secret
    return key, secret


def get_oauth_creds(key):
    # TODO: Throw an exception if key is unknown
    secret = _OAUTH_DB.get(key)
    if secret is None:
        secret = _UNREGISTERED_OAUTH.get(key)
    return secret


def store_session_params(session_id, params):
    _SESSIONS_DB[session_id] = _encode({'upload_token': uuid4().hex,
                                        'tool_provider_params': params})


def verify_resource_oauth(moodle_resource_id, tool_provider):
    resource = _MOODLE_DB.get(moodle_resource_id)
    if resource:    # Resource has been used before
        cred_dict = _decode(resource)
        assert tool_provider.consumer_key == cred_dict.get('consumer_key') and \
               tool_provider.consumer_secret == cred_dict.get('consumer_secret'), \
            "Invalid OAuth credentials for resource"
    else:   # New resource_id, 'register' credentials with it
        key = tool_provider.consumer_key
        _OAUTH_DB[key] = secret = _UNREGISTERED_OAUTH.pop(key)
        _MOODLE_DB[moodle_resource_id] = _encode({'consumer_key': key, 'consumer_secret': secret})


def authorize_user(moodle_uid, context_id, tool_provider):

    activity_string = tool_provider.custom_params.get('custom_box_version')

    # _MOODLE_DB = {
    #   moodle_uid: {'uid': uid, 'username': username}
    #   moodle_resource_id: {'consumer_key': oauth_consumer_key, 'consumer_secret': oauth_shared_secret}
    # }
    moodle_ids = _decode(_MOODLE_DB.setdefault(moodle_uid, _encode(
            {'uid': uuid4().hex, 'username': tool_provider.custom_params.get('lis_person_name_full')})))
    uid = moodle_ids['uid']

    # _USERS_DB = {
    #   context_id: {uid: {'moodle_uid': moodle_uid,
    #                      'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
    #                                'sessions': <list of session_ids>},
    #                      'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
    #                                'sessions': <list of session_ids>}}}
    # }
    context = _decode(_USERS_DB.get(context_id, 'null'))  # 'null' is JSON for None.
    if context is None:
        context = dict()
    user = context.get(uid)
    if user is None:
         user = _new_user(moodle_uid)

    # FIXME: Throw an actual exception
    # FIXME: Crude hack because of poor communication
    #assert user[activity_string]['grade'] < 1.0, "Already completed activity"

    session_id = uuid4().hex

    user[activity_string]['sessions'].append(session_id)
    context[uid] = user
    _USERS_DB[context_id] = _encode(context)

    video_url = _VIDEO_URL.format(session_id=session_id)
    _DATA_DB[session_id] = _encode({'uid': uid, 'video_url': video_url})

    # Generate metadata for session
    # _METADATA_DB = {
    #   session_id: {'uid': uid,
    #                'context': context_id
    #                'activity_string': <activity version string>,
    #                'activity': <activity display name>,
    #                'video_url': <identifier (URL) for video>,
    #                'result': <pass/fail/incomplete status>,
    #                'grade': <completion percentage>,
    #                'return_url': <lti spec 'launch_presentation_return_url'>}
    # }
    metadata = {'uid': uid,
                'context': context_id,
                'activity_string': activity_string,
                'activity': activity_display_name(activity_string),
                'video_url': video_url,
                'result': _INCOMPLETE,
                'grade': 0.0,
                'return_url': tool_provider.launch_presentation_return_url}

    _METADATA_DB[session_id] = _encode(metadata)

    return session_id


def get_ids_from_moodle_uid(moodle_uid):
    return _decode(_MOODLE_DB[moodle_uid])


def get_session_data(session_id):
    return _decode(_DATA_DB[session_id]).get('data', {})


def get_user_data_by_context_id(context_id):
    """
    _USERS_DB = {
    context_id: {uid: {'moodle_uid': moodle_uid,
                       'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>},
                       'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>}}}
    }
    """
    return _decode(_USERS_DB[context_id])


def get_user_data_by_uid(uid, context_id):
    return _decode(_USERS_DB[context_id]).get(uid, dict())


def get_grade(uid, context_id, box_type):
    """
    Returns grade for particular activity.

    _USERS_DB = {
    context_id: {uid: {'moodle_uid': moodle_uid,
                       'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>},
                       'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>}}}
    }
    """
    return _decode(_USERS_DB[context_id])[uid][box_type]['grade']


def store_grade(uid, context_id, box_type, grade):
    """
    _USERS_DB = {
    context_id: {uid: {'moodle_uid': moodle_uid,
                       'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>},
                       'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                 'sessions': <list of session_ids>}}}
    }
    """
    context = _decode(_USERS_DB[context_id])
    context[uid][box_type]['grade'] = grade
    _USERS_DB[context_id] = _encode(context)


def get_ids_for_session(session_id):
    """
    Returns (uid, context_id) for a given session_id.

    _METADATA_DB = {
    session_id: {'uid': uid,
                 'context': context_id
                 'activity': <activity display name>,
                 'video_url': <identifier (URL) for video>,
                 'result': <pass/fail/incomplete status>,
                 'grade': <completion percentage after session, eg. 0%, 33%, 66%, 100%>
                 'version_string': <activity version string>,
                 'return_url': <lti spec 'launch_presentation_return_url'>}
    }
    """
    session = _decode(_METADATA_DB[session_id])
    return session['uid'], session['context']


def get_upload_token(session_id):
    """
    _SESSIONS_DB = {
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    }
    """
    return _decode(_SESSIONS_DB[session_id])['upload_token']


def get_session_params(session_id):
    """
    _SESSIONS_DB = {
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    }
    """
    return _decode(_SESSIONS_DB[session_id])['tool_provider_params']


def store_activity_data(session_id, json_data):
    """
    Store json_data for session_id

    _DATA_DB:
    session_id: {'uid': uid,
                 'video_url': <identifier (URL) for video>,
                 'data': <raw JSON received>}
    """
    session = _decode(_DATA_DB[session_id])
    session['data'] = json_data
    _DATA_DB[session_id] = _encode(session)


def get_result_data(session_id):
    """
    Retrieve json_data for session_id, throw KeyError if not found.

    _DATA_DB:
    session_id: {'uid': uid,
                 'video_url': <identifier (URL) for video>,
                 'data': <raw JSON received>}
    """
    return _decode(_DATA_DB[session_id])['data']


def dump_session_data():
    return dict(_DATA_DB)


def get_metadata(session_id):
    """
    Retreive data from metadata DB for session

    _METADATA_DB = {
        session_id: {'uid': uid,
                     'context': context_id
                     'activity': <activity display name>,
                     'video_url': <identifier (URL) for video>,
                     'result': <pass/fail/incomplete status>,
                     'version_string': <activity version string>,
                     'return_url': <lti spec 'launch_presentation_return_url'>}
    }
    """
    return _decode(_METADATA_DB[session_id])


def store_result(session_id, result, grade):
    """
    Store result for realzies

    _METADATA_DB = {
        session_id: {'uid': uid,
                     'context': context_id
                     'activity': <activity display name>,
                     'video_url': <identifier (URL) for video>,
                     'result': <pass/fail/incomplete status>,
                     'version_string': <activity version string>,
                     'return_url': <lti spec 'launch_presentation_return_url'>}
    }
    """
    session = _decode(_METADATA_DB[session_id])
    session['result'] = result
    session['grade'] = grade
    _METADATA_DB[session_id] = _encode(session)


def delete_session_credentials(session_id):
    """
    _SESSIONS_DB:
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    """
    del _SESSIONS_DB[session_id]


def get_box_name(version):
    return _BOX_VERSION[version]


def activity_display_name(version_string):
    return _ACTIVITY_NAME.get(version_string, "Unknown Activity")


def _new_user(moodle_uid):
    """
    _USERS_DB = {
        context_id: {uid: {'moodle_uid': moodle_uid,
                           'pokey': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                     'sessions': <list of session_ids>},
                           'peggy': {'grade': <completion percentage: 0%, 33%, 66%, 100%>,
                                     'sessions': <list of session_ids>}}}
    }
    """
    return {'moodle_uid': moodle_uid,
            _POKEY: {'grade': 0.0, 'sessions': []},
            _PEGGY: {'grade': 0.0, 'sessions': []}}


_encode = json.dumps

_decode = json.loads
