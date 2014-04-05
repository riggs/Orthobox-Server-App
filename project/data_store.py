# -*- coding: utf-8 -*-
"""
Use lmdb as backend.

Database schema:

1 lmdb environment, 4 databases: sessions, data, users, moodle
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
    moodle_uid: {'uid': uid, 'username': tool_provider.lis_person_name_full}
    moodle_resource_id: {'consumer_key': <OAuth consumer key>, 'consumer_secret': <OAuth shared secret>}
Notes:
    moodle_uid = hashlib.sha1(instance_id + user_id).hexdigest()
    moodle_resource_id = hashlib.sha1(instance_id + resource_id).hexdigest()
    where:
    instance_id = tool_provider.tool_consumer_instance_guid
    user_id = tool_provider.user_id
    resource_id = tool_provider.resource_link_id

"""

from __future__ import division, absolute_import, print_function

from collections import defaultdict
from uuid import uuid4
from hashlib import sha1

import lmdb


fake_DB = {}

def new_id():
    return uuid4().hex