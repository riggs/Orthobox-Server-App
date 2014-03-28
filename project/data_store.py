"""
Fake DB
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'

from collections import defaultdict
from uuid import uuid4

def _DB():
    return defaultdict(_DB)

fake_DB = defaultdict(_DB)



def new_id():
    return str(uuid4())