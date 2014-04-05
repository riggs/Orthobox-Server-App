# -*- coding: utf-8 -*-
"""
Extending ims_lti_py to WebOb
"""

from __future__ import division, absolute_import, print_function


from ims_lti_py.request_validator import RequestValidatorMixin


class WebObRequestValidatorMixin(RequestValidatorMixin):
    """
    An OAuth ToolProvider that works with WebOb requests.
    """
    def parse_request(self, request, parameters, *_, **__):
        """
        Returns a tuple: (method, url, headers, parameters)
        method is the HTTP method: (GET, POST)
        url is the full absolute URL of the request
        headers is a dictionary of any headers sent in the request
        parameters are the parameters sent from the LMS
        """
        return (request.method,
                request.url,
                request.headers,
                request.POST.mixed())
