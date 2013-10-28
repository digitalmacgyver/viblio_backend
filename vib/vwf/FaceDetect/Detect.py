#!/usr/bin/env python

import json
import logging
import pprint
from sqlalchemy import and_

from vib.vwf.VWorker import VWorker

import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

class Detect( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'FaceDetect'
    
    def run_task( self, options ):
        '''Perform the face detection logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''
        
        media_uuid = options['media_uuid']
        user_uuid = options['user_uuid']
        
        # Logging is set up to log to syslog in the parent VWorker class.
        # 
        # In turn syslog is set up to go to our Loggly cloud logging
        # server on our servers.
        #
        # Loggly likes JSON formatted log messages for parsability.
        #
        # Example of how to log, send in a JSON to the logger.  Always
        # include media_uuid and user_uuid if they are in scope /
        # sensible, and always include a message.  Include other keys
        # you'd like to search on when dealing with that message
        # (e.g. s3_key, track_id, whatever)
        log.info( json.dumps( {
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : 'A log message from the face detector.'
                    } ) )


        print "Face detection inputs are:"
        pp = pprint.PrettyPrinter( indent=4 )
        pp.pprint( options )
        print "Doing face detection stuff!"

        print "Config defined in vib/config/viblio.config."

        print "DB Stuff in vib.db.orm"
        orm = vib.db.orm.get_session()
        # Example ORM query - we use the SQLAlchemy and_ construct
        # here to test two things.
        users = orm.query( Users ).filter( and_( Users.email == 'bidyut@viblio.com', Users.displayname != None ) )
        if users.count() == 1:
            print "Bidyut's user id/uuid are %s/%s" % ( users[0].id, users[0].uuid )
        
        recoverable_error = False
        catastrophic_error = False
        if catastrophic_error:
            return { 'ACTIVITY_ERROR' : True, 'retry' : False }
        elif recoverable_error:
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }
        else: 
            # As a placeholder, just pass our input back out.
            return options


