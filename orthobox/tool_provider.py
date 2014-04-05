# -*- coding: utf-8 -*-
"""
Extending ims_lti_py to WebOb
"""

from __future__ import division, absolute_import, print_function

from collections import defaultdict
from ims_lti_py.tool_provider import ToolProvider

from orthobox.request_validator import WebObRequestValidatorMixin
from orthobox.outcome_request import OutcomeRequestOAuthlib


class WebObToolProvider(WebObRequestValidatorMixin, ToolProvider):
    """
    OAuth Tool Provider that works with WebOb requests.
    """
    def new_request(self):
        opts = defaultdict(lambda: None)
        opts.update({
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret,
            'lis_outcome_service_url': self.lis_outcome_service_url,
            'lis_result_sourcedid': self.lis_result_sourcedid
        })
        self.outcome_requests.append(OutcomeRequestOAuthlib(opts=opts))
        self.last_outcome_request = self.outcome_requests[-1]
        return self.last_outcome_request
