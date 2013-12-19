#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import inspect
import json
import logging
from logging import handlers
import mixpanel
import threading
import time
import pdb
import boto
#boto.set_stream_logger('foo')
#ec2 = boto.connect_ec2(debug=2)


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

        heartbeat_timeout = VPW[self.task_name].get( 'default_task_heartbeat_timeout', 'NONE' )
        if heartbeat_timeout == 'NONE':
            self.HEARTBEAT_FREQUENCY = None
        else:
            self.HEARTBEAT_FREQUENCY = int( heartbeat_timeout ) / 3

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
                log.info( json.dumps( {  'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'message' : 'Starting task.'  } ) )               
                #_mp_log( self.task_name + " Started", media_uuid, user_uuid, { 'activity' : self.task_name } )

                self.heartbeat_thread = None
                result = {}
                try:
                    log.info(json.dumps({'message' : 'About to call start_heartbeat...' }))
                    self.heartbeat_active = True
                    self.heartbeat_thread = self.start_heartbeat(self.emit_heartbeat, self.heartbeat)
                    log.info(json.dumps({'message' : 'Running task...' }))
                    result = self.run_task( input_opts )
                finally:
                   log.info(json.dumps({'message' : 'Stopping heartbeat...' }))
                   self.stop_heartbeat()

                if 'ACTIVITY_ERROR' in result:
                    log.error( json.dumps( { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid,
                                'message' : "Task had an error, failing the task with retry: %s" % result.get( 'retry', False ) } ) ) 
                    #_mp_log( self.task_name + " Failed", media_uuid, user_uuid, { 'activity' : self.task_name } )
                    self.fail( details = json.dumps( { 'retry' : result.get( 'retry', False ) } ) )
                else:
                    log.info( json.dumps( {  'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'message' : 'Task completed.' } ) )
                    _mp_log( self.task_name + " Completed", media_uuid, user_uuid, { 'activity' : self.task_name } )
                    self.complete( result = json.dumps( result ) )
                return True
        except Exception as error:
            log = self.logger
            log.error( json.dumps( { 'message' : "Task had an exception: %s" % error } ) )
            self.fail( reason = str( error )[:250] )
            raise error

    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()

    def start_heartbeat(self, emit_heartbeat, heartbeat):
        self.validate_user_method(emit_heartbeat)
        self.validate_user_method(heartbeat)
        
        log = self.logger    
        nsecs = VPW[self.task_name].get('default_task_heartbeat_timeout')
        log.info(json.dumps({'message' : 'heartbeat timeout set in VPWorkflow to %s' % nsecs}))        
        if nsecs == 'NONE':
            return None
        try:
            nsecs = int(nsecs)
        except ValueError:
            log.error(json.dumps({'message' : 'Could not convert %s to int' % nsecs}))
            return None
        else:
            f = self.HEARTBEAT_FREQUENCY
            log.info(json.dumps({'message' : 'HEARTBEAT_FREQUENCY has value %s' % f}))        
            if f <= 1:
                log.error(json.dumps({'message' : 'HEARTBEAT_FREQUENCY must be greater than 1'}))
                return None
            elif nsecs <= f:
                log.error(json.dumps({'message' : 'heartbeat timeout cannot be less than HEARTBEAT_FREQUENCY'}))
                return None
            log.info(json.dumps({'message' : 'Starting heartbeat thread with period %d' % f}))
            t = threading.Thread(target=emit_heartbeat, args = (f, heartbeat))
            t.setDaemon(True) # this makes thread terminate when process that created it terminates
            t.start()
            return t

    def emit_heartbeat(self, delay_secs, heartbeat):
        self.validate_delay_secs(delay_secs)
        self.validate_user_method(heartbeat)

        log = self.logger
        while True:
            heartbeat()
            log.info(json.dumps({'message' : 'Heartbeat just occurred, time to next heartbeat is %d seconds' % delay_secs}))
            for i in range(delay_secs):
                if not self.heartbeat_active:
                    return
                time.sleep(1);

    '''          
    def emit_heartbeat(self, delay_secs, heartbeat):
        self.validate_delay_secs(delay_secs)
        self.validate_user_method(heartbeat)

        log = self.logger
        while self.heartbeat_active:
            heartbeat()
            log.debug(json.dumps({'message' : 'Heartbeat just occurred, will delay %d' % delay_secs}))
            time.sleep(delay_secs);
        return
    '''

    def stop_heartbeat( self ):
        if self.heartbeat_thread is None:
            return
        self.heartbeat_active = False
        self.heartbeat_thread.join()
        self.heartbeat_thread = None

    def validate_delay_secs(self, delay_secs):
        if delay_secs is None:
            raise UnboundLocalError('delay_secs is None')
        elif not isinstance(delay_secs, int):
            raise TypeError('delay_secs is not an int')
        elif delay_secs <= 0:
            raise TypeError('delay_secs must be > 0')

    def validate_user_method(self, var):
        if var is None:
            raise UnboundLocalError('method variable is None')
        elif not inspect.ismethod(var):
            raise TypeError('method variable not a reference to a method')



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
