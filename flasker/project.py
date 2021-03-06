#!/usr/bin/env python

"""Project module."""

from ConfigParser import SafeConfigParser
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from sqlalchemy import create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Query, scoped_session, sessionmaker
from sys import path
from threading import local
from werkzeug.local import LocalProxy

from .util import convert


class _LocalStorage(local):

  """Thread local storage."""
  
  _current_project = None

_local_storage = _LocalStorage()


class ProjectImportError(Exception):

  pass


class Project(object):

  """Project class.

  Global container for the Flask and Celery apps and SQLAlchemy database
  object.
  
  """

  __state = {}
  __registered = False

  config = {
    'PROJECT': {
      'NAME': '',
      'DOMAIN': '',
      'SUBDOMAIN': '',
      'MODULES': '',
      'FLASK_ROOT_FOLDER': 'app',
      'FLASK_STATIC_FOLDER': 'static',
      'FLASK_TEMPLATE_FOLDER': 'templates',
      'COMMIT_ON_TEARDOWN': True,
    },
    'ENGINE': {
      'URL': 'sqlite://',
    },
    'FLASK': {
      'SECRET_KEY': 'a_default_unsafe_key',
    },
    'CELERY': {
      'BROKER_URL': 'redis://',
      'CELERY_RESULT_BACKEND': 'redis://',
      'CELERY_SEND_EVENTS': True
    },
  }

  def __init__(self, config_path=None, make=True):

    self.__dict__ = self.__state
    _local_storage._current_project = self

    if not self.__registered:

      if config_path is None:
        raise ProjectImportError('Project instantiation outside the Flasker '
                                 'command line tool requires a configuration '
                                 'file path.')

      config = self._parse_config(config_path)
      for key in config:
        if key in self.config:
          self.config[key].update(config[key])
        else:
          self.config[key] = config[key]

      self.root_dir = dirname(abspath(config_path))
      self.domain = (
        self.config['PROJECT']['DOMAIN'] or
        sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
      )
      self.subdomain = (
        self.config['PROJECT']['SUBDOMAIN'] or
        splitext(config_path)[0].replace(sep, '-')
      )

      path.append(self.root_dir)

      self.flask = None
      self.celery = None
      self.session = None

      self._engine = None
      self._query_class = Query
      self._before_startup = []

      self.__registered = True

      if make:
        self._make()

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def before_startup(self, func):
    """Decorator, hook to run a function right before project starts."""
    self._before_startup.append(func)

  def _make(self):
    """Create all project components."""

    # core
    for mod in  ['flask', 'celery']:
      __import__('flasker.core.%s' % mod)

    # project modules
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())

    # database
    self._setup_database_connection()

    # final hook
    for func in self._before_startup or []:
      func(self)

  def _setup_database_connection(self):
    """Setup the database engine."""
    engine_ops = dict((k.lower(), v) for k,v in self.config['ENGINE'].items())
    self._engine = create_engine(engine_ops.pop('url'), **engine_ops)
    self.session = scoped_session(
      sessionmaker(bind=self._engine, query_cls=self._query_class)
    )

  def _dismantle_database_connections(self):
    """Remove database connections."""
    try:
      if self.config['PROJECT']['COMMIT_ON_TEARDOWN']:
        self.session.commit()
    except InvalidRequestError as e:
      self.session.rollback()
      self.session.expunge_all()
      raise e
    finally:
      self.session.remove()

  def _parse_config(self, config_path):
    """Read the configuration file and return values as a dictionary.

    Raises ProjectImportError if no configuration file can be read at the
    file path entered.

    """
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive
    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'Unable to parse configuration file at %s.' % config_path
      )
    conf = dict(
      (s, dict((k, convert(v)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )
    if not conf['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')
    return conf


def _get_current_project():
  return _local_storage._current_project or Project()

current_project = LocalProxy(_get_current_project)

