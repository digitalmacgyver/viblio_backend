#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import logging
from logging import handlers
import mixpanel
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

logger = logging.getLogger( 'vib' )
logger.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'vwf: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )

consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

logger.addHandler( syslog )
logger.addHandler( consolelog )

mp = mixpanel.Mixpanel( config.mp_token )
mp_web = mixpanel.Mixpanel( config.mp_web_token )

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

class VWorker( swf.ActivityWorker ):

    def __init__( self, **kwargs ):
        self.domain    = VPW[self.task_name].get( 'domain'   , None )
        self.task_list = VPW[self.task_name].get( 'task_list', '' ) + config.VPWSuffix + config.UniqueTaskList
        self.version   = VPW[self.task_name].get( 'version'  , None )

        super( VWorker, self ).__init__( **kwargs )

        self.logger = logger

    def run( self ):
        try:
            log = self.logger

            log.debug( json.dumps( { 'message' : 'Polling for task.' } ) )

            activity_task = self.poll()

            if 'taskToken' not in activity_task or len( activity_task['taskToken'] ) == 0:
                log.debug( json.dumps( { 'message' : 'Nothing to do.' } ) )
                return True
            else:
                input_opts = json.loads( activity_task['input'] )

                media_uuid = input_opts['media_uuid']
                user_uuid  = input_opts['user_uuid']

                log.info( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : 'Starting task.' 
                            } ) )
                
                #_mp_log( self.task_name + " Started", media_uuid, user_uuid, { 'activity' : self.task_name } )
                result = self.run_task( input_opts )

                if 'ACTIVITY_ERROR' in result:
                    log.error( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'message' : "Task had an error, failing the task with retry: %s" % result.get( 'retry', False ) } ) ) 
                    #_mp_log( self.task_name + " Failed", media_uuid, user_uuid, { 'activity' : self.task_name } )
                    self.fail( details = json.dumps( { 'retry' : result.get( 'retry', False ) } ) )
                else:
                    log.info( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'message' : 'Task completed.'
                                } ) )

                    _mp_log( self.task_name + " Completed", media_uuid, user_uuid, { 'activity' : self.task_name } )

                    self.complete( result = json.dumps( result ) )

                return True

        except Exception as error:
            log.error( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Task had an exception: %s" % error } ) )
            self.fail( reason = str( error ) )
            raise error

    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()


def _mp_log( event, media_uuid, user_uuid, properties = {} ):
    try:
        properties['media_uuid'] = media_uuid
        properties['user_uuid'] = user_uuid
        properties['deployment'] = config.mp_deployment

        mp.track( media_uuid, event, properties )

        if 'user_uuid' in properties:
            mp_web.track( properties['user_uuid'], event, properties )

    except Exception as e:
        logger.warning( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Error sending instrumentation ( %s, %s ) to mixpanel: %s" % ( event, properties, e ) } ) )
