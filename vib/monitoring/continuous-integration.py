#!/usr/bin/env python

import boto.ec2.cloudwatch as cloudwatch
import boto.swf.layer2 as swf
import commands
import json
import logging
from logging import handlers
import os
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *
import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

logger = logging.getLogger( __name__ )
logger.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'continuous_integration: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )

consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

logger.addHandler( syslog )
logger.addHandler( consolelog )

'''
1. git pull to specific path.
2. Alter queues task lists.
3. Send a video.
4. Log an event.
'''


def log_status( status ):
    cw = cloudwatch.connect_to_region( config.cloudwatch_region )
    cw.put_metric_data( config.pipeline_status_domain, 
                        config.pipeline_status_metric, 
                        status,
                        unit = 'Count',
                        dimensions = { 'Deployment' : config.VPWSuffix }
                        )
    return

def send_heartbeat_video( relpath, video ):
    deployment = os.environ.get( 'DEPLOYMENT', 'local' )

    command = '%s/tuspy.py -a %s -s %s -e %s -p %s -f %s' % ( relpath, deployment, deployment, config.monitoring_user, config.monitoring_password, relpath+video )

    ( status, output ) = commands.getstatusoutput( command )
    if status:
        raise Exception( "Error uploading file with tuspy: %s" % ( output ) )

    return

def cleanup_user( user_id, media_uuid = None ):
    if media_uuid != None:
        pass
        #swf.WorkflowExecution( 
        #    name = config.VPWName + config.VPWSuffix,
        #    domain = vib.vwf.VPWorkflow.domain,
        #    version = vib.vwf.VPWorkflow.version
        #    ).terminate( 
        #    domain = vib.vwf.VPWorkflow.domain,
        #    workflow_id = media_uuid
        #    )

    orm = vib.db.orm.get_session()
    if user_id != None:
        orm.query( Media ).filter( and_( Media.user_id == user_id, Media.title == config.pipeline_title ) ).delete()
        orm.commit()
        rec.delete_user( user_id )

    return

try:
    log = logger
    orm = vib.db.orm.get_session()
    
    user = orm.query( Users ).filter( Users.email == config.monitoring_user ).all()

    if len( user ) != 1:
        log.error( json.dumps( { 'message' : '%s user records found for monitoring email %s, expected 1.' % ( len( user ), config.monitoring_user ) } ) )
    else:
        user_uuid = user[0].uuid
        user_id = user[0].id

        heartbeat_media = orm.query( Media ).filter( and_( Media.user_id == user_id, Media.title == config.pipeline_title ) ).all()

        heartbeat_uuid = None
        if len( heartbeat_media ) == 1:
            if heartbeat_media[0].status == 'FaceRecognizeComplete':
                log.debug( json.dumps( { 'message' : 'Pipeline OK' } ) )
                log_status( 1 )
            else:
                heartbeat_uuid = heartbeat_media[0].uuid
                log.debug( json.dumps( { 'message' : 'Pipeline not OK' } ) )
                log_status( 0 )
        else:
            log.debug( json.dumps( { 'message' : 'Pipeline not OK' } ) )
            log_status( 0 )

        cleanup_user( user_id, heartbeat_uuid )
        relpath = os.path.dirname( __file__ )
        if len( relpath ) and relpath[-1] != '/':
            relpath += '/'
        send_heartbeat_video( relpath, config.pipeline_test_video )
except Exception as e:
    print "Error while initiating pipeline: %s" % ( e )
    log.debug( json.dumps( { 'message' : 'Pipeline not OK' } ) )
    log_status( 0 )
