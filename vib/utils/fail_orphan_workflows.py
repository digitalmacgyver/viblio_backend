#!/usr/bin/env python

import datetime
import json
import logging
from optparse import OptionParser
from sqlalchemy import and_, func, not_
import sys
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *

log = logging.getLogger( 'vib.utils.fail_orphan_workflows' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'fail_orphan_workflows: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def fail_orphan_workflows( hours=24*3 ):
    '''Search our database for media records that are in 'pending' and
    change them to failed.'''
    
    try:
        orm = None
        orm = vib.db.orm.get_session()

        from_when = datetime.datetime.utcnow() - datetime.timedelta( hours=hours )

        orphan_workflows = orm.query( Media ).filter( and_( Media.status == 'pending', Media.created_date <= from_when ) ).all()
        
        log.debug( json.dumps( { 'message' : "Found %d orphan workflows." % len( orphan_workflows ) } ) )

        for orphan in orphan_workflows:
            orphan.status = 'failed'

            mwfs = MediaWorkflowStages( workflow_stage = 'WorkflowFailed' )
            
            orphan.media_workflow_stages.append( mwfs )

            log.debug( json.dumps( { 'media_uuid' : orphan.uuid,
                                     'message' : "Set status to failed for media_uuid %s" %  ( orphan.uuid ) } ) )

        orm.commit()

        return True

    except Exception as e:
        if orm != None:
            orm.rollback()
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise

def complete_visible_workflows( hours=24*3 ):
    '''Search for workflows that are 'visible' and older than the
    threshold - set their status to 'complete'.'''
    
    try:
        orm = None
        orm = vib.db.orm.get_session()

        from_when = datetime.datetime.utcnow() - datetime.timedelta( hours=hours )

        orphan_workflows = orm.query( Media ).filter( and_( Media.status == 'visible', Media.created_date <= from_when ) ).all()
        
        log.debug( json.dumps( { 'message' : "Found %d timed out visible workflows." % len( orphan_workflows ) } ) )

        for orphan in orphan_workflows:
            orphan.status = 'complete'

            mwfs = MediaWorkflowStages( workflow_stage = 'WorkflowFailed' )
            
            orphan.media_workflow_stages.append( mwfs )

            log.debug( json.dumps( { 'media_uuid' : orphan.uuid,
                                     'message' : "Set status to complete for media_uuid %s" %  ( orphan.uuid ) } ) )

        orm.commit()

        return True

    except Exception as e:
        if orm != None:
            orm.rollback()
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise
    
if __name__ == '__main__':
    try:
        fail_orphan_workflows()
        complete_visible_workflows()
    except Exception as e:
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise
