import web
import json
import uuid
import hmac
from models import *
import os

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

import sys
import boto
import requests
from boto.s3.key import Key

import mimetypes

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

def sync( c, orm, log ):
    log.debug( "Doing a Facebook Sync for user: " + c['uid'] )

def unsync( c, orm, log ):
    log.debug( "Doing a Facebook Un-Sync for user: " + c['uid'] )
