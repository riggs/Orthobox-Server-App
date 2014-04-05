"""
To disable .pyc caching:

$ python -B

or for ipython create the following ~/.ipython/profile_default/startup/autoreload.ipy:

# Autoreload will pick up changes in imported things and reload them as needed
%load_ext autoreload
%autoreload 2
"""
from __future__ import division, absolute_import, print_function

__author__ = 'riggs'

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.request import Request

from orthobox import _custom_config

def serve():
    config = _custom_config(Configurator())
    app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 8128, app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        del server


example_request = """POST /echo/candy HTTP/1.1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Encoding: gzip,deflate,sdch
Accept-Language: en-US,en;q=0.8
Cache-Control: max-age=0
Connection: keep-alive
Content-Length: 1336
Content-Type: application/x-www-form-urlencoded
Host: dev.xlms.org:6969
Origin: http://dev.xlms.org
Referer: http://dev.xlms.org/moodle/mod/lti/launch.php?id=32
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36

oauth_version=1.0&oauth_nonce=d330261b8a4976e16431867f38389d09&oauth_timestamp=1395899693&oauth_consumer_key=consumer_key&custom_box_version=pokey_dev&resource_link_id=10&resource_link_title=candy&resource_link_description=&user_id=2&roles=Instructor%2Curn%3Alti%3Asysrole%3Aims%2Flis%2FAdministrator&context_id=4&context_label=ORTH+1001&context_title=Ortho+Boxes&launch_presentation_locale=en&lis_result_sourcedid=%7B%22data%22%3A%7B%22instanceid%22%3A%2210%22%2C%22userid%22%3A%222%22%2C%22launchid%22%3A1903112781%7D%2C%22hash%22%3A%2298e51e10f0569b5fc66d94d9b62b4925e5e9db00de5b28f0745eb1c64891b956%22%7D&lis_outcome_service_url=http%3A%2F%2Fdev.xlms.org%2Fmoodle%2Fmod%2Flti%2Fservice.php&lis_person_name_given=Admin&lis_person_name_family=User&lis_person_name_full=Admin+User&lis_person_contact_email_primary=deisum%40gmail.com&ext_lms=moodle-2&tool_consumer_info_product_family_code=moodle&tool_consumer_info_version=2013111802&oauth_callback=about%3Ablank&lti_version=LTI-1p0&lti_message_type=basic-lti-launch-request&tool_consumer_instance_guid=dev.xlms.org&launch_presentation_return_url=http%3A%2F%2Fdev.xlms.org%2Fmoodle%2Fmod%2Flti%2Freturn.php%3Fcourse%3D4%26launch_container%3D2%26instanceid%3D10&oauth_signature_method=HMAC-SHA1&oauth_signature=fYoyMTayHYHicWb%2Bh8yErF%2BxrWs%3D&ext_submit=Press+to+launch+this+activity"""

req = Request.from_string(example_request)

if __name__ == "__main__":
    serve()
