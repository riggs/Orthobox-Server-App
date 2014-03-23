"""
Extending ims_lti_py to WebOb
"""

from __future__ import division, absolute_import, print_function
__author__ = 'riggs'


from .request_validator import WebObRequestValidatorMixin

from ims_lti_py.tool_provider import ToolProvider


class WebObToolProvider(WebObRequestValidatorMixin, ToolProvider):
    """
    OAuth Tool Provider that works with WebOb requests.
    """
    pass
