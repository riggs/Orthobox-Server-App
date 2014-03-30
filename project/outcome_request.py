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

        outcome_response = OutcomeResponse()
        outcome_response.post_response = response
        outcome_response.response_code = response.status_code
        outcome_response.process_xml(response.text)

        self.outcome_response = outcome_response
        return outcome_response
