# -*- coding: utf-8 -*-
"""
Main entry point
"""
from pyramid.config import Configurator

from orthobox import data_store; del data_store    # Instantiate DB

def _custom_config(config):
    # TODO: See if traversal & cornice will play nicely enough
    config.include("cornice")
    config.include("pyramid_chameleon")
    config.add_renderer(name='csv', factory='orthobox.lti_views.CSV_Renderer')  # Thank you stackoverflow
    config.scan("orthobox.rest_views")
    config.add_route('lti_launch', 'launch')
    config.add_route('lti_progress', 'progress')
    config.add_route('lti_csv_export', 'csv_export')
    config.add_route('lti_simple_csv_export', 'simple_csv_export')
    config.scan("orthobox.lti_views")
    return config

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config = _custom_config(config)
    return config.make_wsgi_app()
