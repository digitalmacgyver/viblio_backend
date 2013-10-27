#!/usr/bin/env python

import json
import pprint

from vib.vwf.VWorker import VWorker

import vib.db.orm
from vib.db.models import *
from sqlalchemy import and_

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

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
        print "Face detection inputs are:"
        pp = pprint.PrettyPrinter( indent=4 )
        pp.pprint( options )
        print "Doing face detection stuff!"

        print "Config defined in vib/config/viblio.config."

        print "DB Stuff in vib.db.orm"
        orm = vib.db.orm.get_session()
        # Example ORM Questy - we use the SQLAlchemy and_ construct
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
            return { 'media_uuid' : 1234, 'user_uuid' : 4567, 'tracks' : [ { 's3url' : 'blahblahblah' } ] }

