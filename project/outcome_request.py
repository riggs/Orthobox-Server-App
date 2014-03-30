"""
Subclassing to replace failing OAuth functionality.
"""

from __future__ import absolute_import

from ims_lti_py import OutcomeRequest, OutcomeResponse
from project.body_hash_oauth1 import BodyHashOAuth1Session


class OutcomeRequestOAuthlib(OutcomeRequest):

    def post_outcome_request(self):
        """
        POST an OAuth signed request to the Tool Consumer.
        """
        session = BodyHashOAuth1Session(self.consumer_key, self.consumer_secret)

        body = self.generate_request_xml()
        headers = {'Content-Type': 'application/xml'}

        response = session.post(self.lis_outcome_service_url, data=body, headers=headers)
        content = response.text

        self.outcome_response = OutcomeResponse.from_post_response(response,
                                                                   content)
        return self.outcome_response
