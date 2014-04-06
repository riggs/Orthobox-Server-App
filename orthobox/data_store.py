# -*- coding: utf-8 -*-
"""
Use lmdb as backend.

Database schema:

1 lmdb environment, 7 databases: sessions, data, metadata, users, moodle, oauth, unregistered_oauth
DB keys: utf-8 encoded text
DB values: utf-8 encoded JSON
uid = uuid4().hex
session_id = uuid4().hex

sessions:
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
Note: Remove after successful use

data:   # 'Sanitized' copy to be kept for later analysis.
    session_id: {'uid': uid
                 'video': <identifier (URL) for video>,
                 'data': <raw JSON received>}

metadata:
    session_id: {'username': username,
                 'activity': <activity display name>,
                 'video': <identifier (URL) for video>,
                 'result': <pass/fail/incomplete status>,
                 'version': <activity version string>}

users:
    uid: {'moodle_uid': moodle_uid,
          'sessions': <list of session_ids>}

moodle:
    moodle_uid: uid
    moodle_resource_id: {'consumer_key': <OAuth consumer key>, 'consumer_secret': <OAuth shared secret>}
Notes:
    moodle_uid = hashlib.sha1(instance_id + user_id).hexdigest()
    moodle_resource_id = hashlib.sha1(instance_id + resource_id).hexdigest()
    where:
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id

oauth:
    oauth_consumer_key: oauth_consumer_secret

unregistered_oauth:
    oauth_consumer_key: oauth_consumer_secret
Note: Keys are created in unregistered, then moved to oauth once associated with moodle_resource_id
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import json
import lmdb

from os import environ
from uuid import uuid4
from hashlib import sha1

from orthobox.evaluation import activity_name, _INCOMPLETE
from orthobox.lmdb_wrapper import LMDB_Dict

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

_VIDEO_URL = "https://s3.amazonaws.com/orthoboxes-video/{session_id}.mp4"


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


def new_session(tool_provider):
    """
    Generate new session data
    """
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id
    moodle_uid = _sha1_hex(instance_id, user_id)
    moodle_resource_id = _sha1_hex(instance_id, resource_id)

    # Verify OAuth creds for this resource
    resource = _MOODLE_DB.get(moodle_resource_id)
    if resource:    # Resource have been used before
        cred_dict = _decode(resource)
        assert tool_provider.consumer_key == cred_dict.get('consumer_key') and \
               tool_provider.consumer_secret == cred_dict.get('consumer_secret'),\
            "Invalid OAuth credentials for resource"
    else:   # New resource_id, 'register' credentials with it
        key = tool_provider.consumer_key
        _OAUTH_DB[key] = secret = _UNREGISTERED_OAUTH.pop(key)
        _MOODLE_DB[moodle_resource_id] = _encode({'consumer_key': key, 'consumer_secret': secret})

    session_id = uuid4().hex

    _SESSIONS_DB[session_id] = _encode({'upload_token': uuid4().hex,
                                        'tool_provider_params': tool_provider.params})

    # moodle_uid: uid
    # moodle_resource_id: {'consumer_key': oauth_consumer_key, 'consumer_secret': oauth_shared_secret}
    uid = _MOODLE_DB.setdefault(moodle_uid, uuid4().hex)

    user = _decode(_USERS_DB.setdefault(uid, _encode({'moodle_uid': moodle_uid, 'sessions': []})))
    user['sessions'].append(session_id)
    _USERS_DB[uid] = _encode(user)

    video_url = _VIDEO_URL.format(session_id=session_id)
    _DATA_DB[session_id] = _encode({'uid': uid, 'video': video_url})

    # Generate metadata for session
    # session_id: {'username': username,
    #              'activity': <activity display name>,
    #              'video': <identifier (URL) for video>,
    #              'result': <pass/fail/incomplete status>,
    #              'version': <activity version string>}
    metadata = {}
    metadata['username'] = tool_provider.username(default="lovely")
    metadata['version'] = version = tool_provider.custom_params.get('custom_box_version')
    metadata['activity'] = activity_name(version)
    metadata['video'] = video_url
    metadata['result'] = _INCOMPLETE

    _METADATA_DB[session_id] = _encode(metadata)

    return session_id


def get_upload_token(session_id):
    """
    _SESSIONS_DB:
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    """
    return _decode(_SESSIONS_DB[session_id])['upload_token']


def get_session_params(session_id):
    """
    _SESSIONS_DB:
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    """
    return _decode(_SESSIONS_DB[session_id])['tool_provider_params']


def store_result_data(session_id, json_data):
    """
    Store json_data for session_id

    _DATA_DB:
    session_id: {'uid': uid,
                 'video': <identifier (URL) for video>,
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
                 'video': <identifier (URL) for video>,
                 'data': <raw JSON received>}
    """
    return _decode(_DATA_DB[session_id])['data']


def get_metadata(session_id):
    """
    Retreive data from metadata DB for session

    metadata:
        session_id: {'username': username,
                     'activity': <activity display name>,
                     'video': <identifier (URL) for video>,
                     'result': <pass/fail/incomplete status>,
                     'version': <activity version string>}
    """
    return _decode(_METADATA_DB[session_id])


def delete_session_credentials(session_id):
    """
    _SESSIONS_DB:
    session_id: {'upload_token': token,
                 'tool_provider_params': tool_provider.params}
    """
    del _SESSIONS_DB[session_id]


_encode = json.dumps

_decode = json.loads


def _sha1_hex(*args):
    h = sha1()
    for item in args:
        h.update(item)
    return h.hexdigest()