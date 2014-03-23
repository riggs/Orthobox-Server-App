"""Main entry point
"""
from pyramid.config import Configurator


def main(global_config, **settings):
    config = Configurator(settings=settings)
    # TODO: See if traversal & cornice will play nicely enough
    config.include("cornice")
    config.include("pyramid_chameleon")
    config.scan("project.rest_views")
    config.add_route('lti_root', 'lti')
    config.add_route('lti', 'lti/{path}')
    config.scan("project.lti_views")
    return config.make_wsgi_app()
