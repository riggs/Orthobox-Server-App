# -*- coding: utf-8 -*-
"""
Main entry point
"""
from pyramid.config import Configurator

def _custom_config(config):
    # TODO: See if traversal & cornice will play nicely enough
    config.include("cornice")
    config.include("pyramid_chameleon")
    config.scan("orthobox.rest_views")
    config.add_route('lti_launch', 'launch')
    config.scan("orthobox.lti_views")
    return config

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config = _custom_config(config)
    return config.make_wsgi_app()
