__author__ = 'riggs'

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.request import Request

def serve():
    config = Configurator()
    config.include("cornice")
    config.include("pyramid_chameleon")
    config.scan("project.rest_views")
    config.add_route('lti_root', 'lti')
    config.add_route('lti', 'lti/{path}')
    config.scan('project.lti_views')
    app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 8080, app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        del server

_request_string = """POST /lit/launch HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Encoding: gzip,deflate,sdch
Accept-Language: en-US,en;q=0.8
Cache-Control: max-age=0
Connection: keep-alive
Content-Length: 1379
Content-Type: application/x-www-form-urlencoded
Host: dev.xlms.org:6969
Origin: http://dev.xlms.org
Referer: http://dev.xlms.org/moodle/mod/lti/launch.php?id=31
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36

oauth_version=1.0&oauth_nonce=5b3115b2634cf3127e71715f4fd71eba&oauth_timestamp=1395574928&oauth_consumer_key=consumer_key&custom_custom_parameter=42&resource_link_id=9&resource_link_title=LTI+test&resource_link_description=%3Cp%3EImplementing+the+LTI+protocol.%3C%2Fp%3E&user_id=2&roles=Instructor%2Curn%3Alti%3Asysrole%3Aims%2Flis%2FAdministrator&context_id=4&context_label=ORTH+1001&context_title=Ortho+Boxes&launch_presentation_locale=en&lis_result_sourcedid=%7B%22data%22%3A%7B%22instanceid%22%3A%229%22%2C%22userid%22%3A%222%22%2C%22launchid%22%3A1131952936%7D%2C%22hash%22%3A%225348b858454bc9c4ed1c0976fe3f5131aeace9e942f0fc9a67d13fd5d78a4e04%22%7D&lis_outcome_service_url=http%3A%2F%2Fdev.xlms.org%2Fmoodle%2Fmod%2Flti%2Fservice.php&lis_person_name_given=Admin&lis_person_name_family=User&lis_person_name_full=Admin+User&lis_person_contact_email_primary=deisum%40gmail.com&ext_lms=moodle-2&tool_consumer_info_product_family_code=moodle&tool_consumer_info_version=2013111802&oauth_callback=about%3Ablank&lti_version=LTI-1p0&lti_message_type=basic-lti-launch-request&tool_consumer_instance_guid=dev.xlms.org&launch_presentation_return_url=http%3A%2F%2Fdev.xlms.org%2Fmoodle%2Fmod%2Flti%2Freturn.php%3Fcourse%3D4%26launch_container%3D2%26instanceid%3D9&oauth_signature_method=HMAC-SHA1&oauth_signature=%2B4T3h8Kk7TML2rMaTI295QPToeM%3D&ext_submit=Press+to+launch+this+activity"""

req = Request.from_string(_request_string)