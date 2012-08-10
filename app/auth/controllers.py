#!/usr/bin/env python

"""This is where the auth magic happens."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import request
from flask.ext.login import LoginManager

from json import loads

from urllib import urlencode
from urllib2 import Request, urlopen

# App level imports

from app.conf.flask import AuthConfig
from app.core.database import Session

import models as m

# Login manager instance
# ======================

login_manager = LoginManager()

login_manager.login_view = '/sign_in'
login_manager.login_message = ("A little bird tells me you have to sign in"
                               " before coming here.")

@login_manager.user_loader
def load_user(user_email):
    """Return the user from his email.

    :param user_email: user email
    :type user_email: string
    :rtype: User

    Necessary for flask.login module.
    
    """
    with Session() as session:
        user = session.query(m.User).filter(
                m.User.email == user_email
        ).first()
    return user

# Google API helpers
# ==================

class OAuth(AuthConfig):

    """Contains variables used for the Google authentication process."""

    ENDPOINTS = {
            'get_token_or_code': "https://accounts.google.com/o/oauth2/auth",
            'validate_token': "https://www.googleapis.com/oauth2/v1/tokeninfo",
            'get_token_from_code': "https://accounts.google.com/o/oauth2/token",
            'get_user_info': "https://www.googleapis.com/oauth2/v2/userinfo",
    }
    SCOPES = {
            'email': "https://www.googleapis.com/auth/userinfo.email",
            'profile': "https://www.googleapis.com/auth/userinfo.profile"
    }
    RESPONSE_TYPE = "token"
    GRANT_TYPE = "authorization_code"
    ACCESS_TYPE = "offline"

def get_params():
    """Builds the dictionary of parameters required the API request.

    :rtype: dict

    """
    if 'next' in request.args:
        state = request.args['next']
    else:
        state = '/'
    return {'scope': OAuth.SCOPES['email'],
            'redirect_uri': OAuth.REDIRECT_URI,
            'response_type': OAuth.RESPONSE_TYPE,
            'state': state,
            'client_id': OAuth.CLIENT_ID}

def get_google_login_url():
    """Combines the endpoint with the parameters to generate the API url.

    :rtype: string

    """
    return (OAuth.ENDPOINTS['get_token_or_code'] + '?' + 
                           urlencode(get_params()))

def validate_token(token):
    """Checks if the token is valid.

    :param token: auth token
    :type token: string
    :rtype: boolean

    """
    url = OAuth.ENDPOINTS['validate_token'] + '?access_token=' + token
    req = Request(url)
    token_info = loads(urlopen(req).read())
    if 'error' in token_info:
        return False
    else:
        return True

def get_user_info_from_token(token):
    """Grabs user email from token.

    :param token: auth token
    :type token: string
    :rtype: dict

    """
    url = OAuth.ENDPOINTS['get_user_info']
    headers = {'Authorization': 'Bearer ' + token}
    req = Request(url, headers=headers)
    res = loads(urlopen(req).read())
    return res
