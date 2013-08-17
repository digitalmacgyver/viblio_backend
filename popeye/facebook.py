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

from background import Background

class FacebookSync(Background):
    def run( self ):
        orm = self.orm
        log = self.log
        c   = self.data
        log.debug( "Doing a Facebook Sync for user: " + c['uid'] )
        for user in orm.query( Users ).order_by( Users.id ):
            print "%s: %s" % ( user.email, user.uuid )

class FacebookUnsync(Background):
    def run( self ):
        self.log.debug( "Doing a Facebook Un-Sync for user: " + self.data['uid'] )
