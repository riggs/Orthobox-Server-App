# -*- coding: utf-8 -*-
"""
Use lmdb as backend.

Database schema:

1 lmdb environment, 6 databases: sessions, data, users, moodle, oauth, unregistered_oauth
DB keys: utf-8 encoded text
DB values: utf-8 encoded JSON
uid = uuid4().hex
session_id = uuid4().hex

sessions:
    session_id: {'upload_token': token,
                 'grade_token': tool_provider.lis_result_sourcedid}
Note: Remove each after successful use; remove entry once empty

data:
    session_id: {'uid': uid
                 'video': <identifier (URL) for video>,
                 'data': <raw JSON received>}

users:
    uid: {'moodle_uid': moodle_uid,
          'sessions': <list of session_ids>}

moodle:
    moodle_uid: {'uid': uid, 'username': tool_provider.username}
    moodle_resource_id: {'consumer_key': <OAuth consumer key>, 'consumer_secret': <OAuth shared secret>}
Notes:
    moodle_uid = hashlib.sha1(instance_id + user_id).hexdigest()
    moodle_resource_id = hashlib.sha1(instance_id + resource_id).hexdigest()
    where:
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id

"""

from __future__ import division, absolute_import, print_function, unicode_literals

from os import environ
from uuid import uuid4
from hashlib import sha1

import lmdb

from orthobox.lmdb_wrapper import LMDB


_LMDB_DATADIR = environ.get('LMDB_DATADIR', 'lmdb_data')
_LMDB_ENV = lmdb.open(_LMDB_DATADIR, max_dbs=5)

_SESSIONS_DB = LMDB(_LMDB_ENV, 'sessions')
_DATA_DB = LMDB(_LMDB_ENV, 'data')
_USERS_DB = LMDB(_LMDB_ENV, 'users')
_MOODLE_DB = LMDB(_LMDB_ENV, 'moodle')
_OAUTH_DB = LMDB(_LMDB_ENV, 'oauth')
_UNREGISTERED_OAUTH = LMDB(_LMDB_ENV, 'unregistered_oauth')


def new_OAuth_creds():
    # TODO: Authentication so this can be run automatically
    key = uuid4().hex
    secret = uuid4().hex
    _UNREGISTERED_OAUTH[key] = secret
    return key, secret


def get_OAuth_creds(key):
    # TODO: Throw an exception if key is unknown
    secret = _OAUTH_DB.get(key)
    if secret is None:
        secret = _UNREGISTERED_OAUTH.get(key)
    return secret


def new_session(tool_provider):
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id
    moodle_uid = sha1(instance_id + user_id).hexdigest()
    moodle_resource_id = sha1(instance_id + resource_id).hexdigest()
    # Verify OAuth creds for this resource

    session_id = new_id()


def new_id():
    return uuid4().hex