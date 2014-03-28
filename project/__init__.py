"""Main entry point
"""
from pyramid.config import Configurator

def _custom_config(config):
    # TODO: See if traversal & cornice will play nicely enough
    config.include("cornice")
    config.include("pyramid_chameleon")
    config.scan("project.rest_views")
    #config.add_route('lti_root', 'lti')
    config.add_route('lti', 'lti/{path}')
    config.scan("project.lti_views")
    return config

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config = _custom_config(config)
    return config.make_wsgi_app()
