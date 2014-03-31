"""
Subclassing to replace failing OAuth functionality.
"""

from __future__ import absolute_import

from lxml import etree

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

    def generate_request_xml(self):
        root = etree.Element('imsx_POXEnvelopeRequest', xmlns='http://www.imsglobal.org/lis/oms1p0/pox')

        header = etree.SubElement(root, 'imsx_POXHeader')
        header_info = etree.SubElement(header, 'imsx_POXRequestHeaderInfo')
        version = etree.SubElement(header_info, 'imsx_version')
        version.text = 'V1.0'
        message_identifier = etree.SubElement(header_info,
                                              'imsx_messageIdentifier')
        message_identifier.text = self.message_identifier
        body = etree.SubElement(root, 'imsx_POXBody')
        request = etree.SubElement(body, '%s%s' %(self.operation, 'Request'))
        record = etree.SubElement(request, 'resultRecord')

        guid = etree.SubElement(record, 'sourcedGUID')

        sourcedid = etree.SubElement(guid, 'sourcedId')
        sourcedid.text = self.lis_result_sourcedid

        if self.score:
            result = etree.SubElement(record, 'result')
            result_score = etree.SubElement(result, 'resultScore')
            language = etree.SubElement(result_score, 'language')
            language.text = 'en'
            text_string = etree.SubElement(result_score, 'textString')
            text_string.text = self.score.__str__()

        return etree.tostring(root, xml_declaration=True, encoding='utf-8')
