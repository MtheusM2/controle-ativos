"""
Entry point WSGI para Gunicorn, uWSGI ou qualquer servidor compatível.
"""

from web_app.app import application


app = application