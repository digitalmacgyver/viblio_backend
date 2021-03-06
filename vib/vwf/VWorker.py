#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import vib.vwf.CheckerUtils as CheckerUtils
import json
import logging
from logging import handlers
import mixpanel
import vib.utils.Serialize as Serialize
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

import pdb

class VWorker( swf.ActivityWorker ):

    def __init__( self, **kwargs ):
        self.domain    = VPW[self.task_name].get( 'domain'   , None )
        self.task_list = VPW[self.task_name].get( 'task_list', '' ) + config.VPWSuffix + config.UniqueTaskList
        self.version   = VPW[self.task_name].get( 'version'  , None )
        self.lock_wait_secs = VPW[self.task_name].get('lock_wait_secs', None)
        self.lock_heartbeat_secs = VPW[self.task_name].get('lock_heartbeat_secs', None)

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
                result = self.manage_run_task(activity_task['taskToken'], input_opts)
                if 'LOCK_ERROR' in result:
                    log.error( json.dumps( { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid,
                                'message' : "Task had an error: could not acquire lock"} ) ) 
                    self.fail(details = json.dumps({'retry':True }), reason = 'no_lock')
                elif 'ACTIVITY_ERROR' in result:
                    log.error( json.dumps( { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid,
                                'message' : "Task had an error, failing the task with retry: %s" % result.get( 'retry', False ) } ) ) 
                    #_mp_log( self.task_name + " Failed", media_uuid, user_uuid, { 'activity' : self.task_name } )
                    self.fail( details = json.dumps( { 'retry' : result.get( 'retry', False ) } ) )
                else:
                    log.info( json.dumps( {  'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'message' : 'Task completed.' } ) )
                    if self.task_name == 'Transcode':
                        # Special call here for transcode to increment the per user count on visible videos.
                        _mp_log( self.task_name + " Completed", media_uuid, user_uuid, { 'activity' : self.task_name }, user_increment = { 'Video Visible' : 1 } )
                    else:
                        _mp_log( self.task_name + " Completed", media_uuid, user_uuid, { 'activity' : self.task_name } )

                    self.complete( result = json.dumps( result ) )
                return True
        except Exception as error:
            log = self.logger
            log.error( json.dumps( { 'message' : "Task had an exception: %s" % error } ) )
            self.fail( reason = str( error )[:250] )
            raise error

    def manage_run_task(self, task_token, input_options):
        CheckerUtils.validate_string(task_token)
        CheckerUtils.validate_dict(input_options)

        log = self.logger
        lock = None
        self.heartbeat_thread = None
        try:
            self.heartbeat_active = True
            self.heartbeat_thread = self.start_heartbeat(self.emit_heartbeat, self.heartbeat)
            mid = input_options['media_uuid']
            uid = input_options['user_uuid']
            wait = input_options.get('lock_wait', False)
            if wait and self.lock_wait_secs is not None:
                try:
                    nsecs = self.lock_wait_secs
                    nsecs = int(nsecs)
                except ValueError:
                    message = 'Could not convert lock_wait_secs value of %s to int' % nsecs
                    log.error(json.dumps({'message' : message}))
                else:
                    message = 'Sleeping for %s seconds before retrying lock acquisition' % nsecs
                    log.info(json.dumps({'message' : message }))               
                    time.sleep(nsecs)
            lock = Serialize.Serialize(self.task_name[:64], mid[:64], task_token[:64], config, heartbeat=self.lock_heartbeat_secs)
            if lock.acquire(blocking=False):
                log.info( json.dumps( {  'media_uuid' : mid, 'user_uuid' : uid, 'message' : 'Starting task.'  } ) )               
                #_mp_log( self.task_name + " Started", mid, uid, { 'activity' : self.task_name } )
                return self.run_task(input_options)
            else:
                log.error(json.dumps({'media_uuid' : mid, 'user_uuid' : uid, 'message' : "Task had an error: could not acquire lock"} ) ) 
                return {'LOCK_ERROR' : True}
        finally:
            log.info(json.dumps({'message' : 'Releasing lock if held...' }))
            if lock:
                lock.release()
            log.info(json.dumps({'message' : 'Stopping heartbeat...' }))
            self.stop_heartbeat()    
    
    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()

    def start_heartbeat(self, emit_heartbeat, heartbeat):
        CheckerUtils.validate_user_method(emit_heartbeat)
        CheckerUtils.validate_user_method(heartbeat)
        
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
        CheckerUtils.validate_user_method(heartbeat)

        log = self.logger
        while True:
            if self.heartbeat_active:
                heartbeat()
            else:
                return
            log.info(json.dumps({'message' : 'Heartbeat just occurred, time to next heartbeat is %d seconds' % delay_secs}))
            for i in range(delay_secs):
                if not self.heartbeat_active:
                    return
                time.sleep(1);

    def stop_heartbeat( self ):
        if self.heartbeat_thread is None:
            return
        self.heartbeat_active = False
        self.heartbeat_thread.join()
        self.heartbeat_thread = None

    def validate_delay_secs(self, delay_secs):
        CheckerUtils.validate_int(delay_secs)
        if delay_secs <= 0:
            raise ValueError('delay_secs must be > 0')

def _mp_log( event, media_uuid, user_uuid, properties = {}, user_increment = {} ):
    try:
        properties['media_uuid'] = media_uuid
        properties['user_uuid'] = user_uuid
        properties['deployment'] = config.mp_deployment

        mp.track( media_uuid, event, properties )

        if 'user_uuid' in properties:
            mp_web.track( properties['user_uuid'], event, properties )
            if user_increment:
                mp_web.people_increment( properties['user_uuid'], user_increment )

    except Exception as e:
        logger.warning( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Error sending instrumentation ( %s, %s ) to mixpanel: %s" % ( event, properties, e ) } ) )
