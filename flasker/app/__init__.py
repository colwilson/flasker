#!/usr/bin/env python

"""App factory module."""

from logging import getLogger
from logging.config import dictConfig

from app.core.config import BaseConfig, DebugConfig, LoggerConfig, \
PROJECT_NAME, STATIC_SERVER_URL, USE_CELERY, USE_OAUTH
from app.core.database import db
from app.views import app as the_app

if USE_CELERY:
  from app.core.config import CeleryBaseConfig, CeleryDebugConfig
  from app.core.celery import celery

if USE_OAUTH:
  from flask.ext.login import current_user
  from app.core.auth import initialize_bp as init_core_bp

logger = getLogger(__name__)

# The app factory!
# ================

@the_app.context_processor
def inject():
  def static_url(request):
    return STATIC_SERVER_URL or request.url_root + 'static/assets'
  def is_logged_in():
    return USE_OAUTH and current_user.is_authenticated()
  return {
    'project_name': PROJECT_NAME,
    'static_url': static_url,
    'is_logged_in': is_logged_in
  }

def make_app(debug=False):
  """App factory."""
  if debug:
    dictConfig(LoggerConfig.DEBUG_LOGGER_CONFIG)
    the_app.config.from_object(DebugConfig)
  else:
    the_app.config.from_object(BaseConfig)
    dictConfig(LoggerConfig.LOGGER_CONFIG)
  if USE_CELERY:
    if debug:
      celery.config_from_object(CeleryDebugConfig)
    else:
      celery.config_from_object(CeleryBaseConfig)
  if USE_OAUTH:
    init_core_bp(the_app, debug)
  return the_app