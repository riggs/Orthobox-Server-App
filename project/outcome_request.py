"""
Subclassing to replace failing OAuth functionality.
"""

import hashlib
import base64
from requests_oauthlib import OAuth1Session

from ims_lti_py import OutcomeRequest


class OutcomeRequest(OutcomeRequest):

    def post_outcome_request(self):
        '''
        POST an OAuth signed request to the Tool Consumer.
        '''
        session = OAuth1Session(self.consumer_key, self.consumer_secret)

        body = self.generate_request_xml()
        headers = {'Content-Type': 'application/xml'}
        oauth_body_hash = 'oauth_body_hash="{0}"'.format(base64.b64encode(hashlib.sha1(body).digest()))

        response = session.post(self.lis_outcome_service_url, data=body, headers=headers)