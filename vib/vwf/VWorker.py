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

logger = logging.getLogger( 'vib.vwf' )
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
    HEARTBEAT_FREQUENCY = 3

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
                   self.stop_heartbeat(self.heartbeat_thread)

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
            self.fail( reason = str( error ) )
            raise error

    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()

    def start_heartbeat(self, emit_heartbeat, heartbeat):
        self.validateUserMethod(emit_heartbeat)
        self.validateUserMethod(heartbeat)
        
        nsecs = VPW[self.task_name].get('default_task_heartbeat_timeout')
        if nsecs == 'NONE':
            return None
        log = self.logger
        log.info(json.dumps({'message' : 'Heartbeat timeout = %s' % nsecs}))
        try: 
            nsecs = int(nsecs)
        except ValueError:
            log.error(json.dumps({'message' : 'Could not convert %s to int' % nsecs}))
            return None
        else:
            nsecs /= VWorker.HEARTBEAT_FREQUENCY

            #nsecs = 1

            log.info(json.dumps({'message' : 'Starting heartbeat...'})) 
            t = threading.Thread(target=emit_heartbeat, args = (nsecs, heartbeat))
            t.setDaemon(True) # this makes thread terminate when process that created it terminates
            t.start()
            return t

    def emit_heartbeat(self, delay_secs, heartbeat):
        self.validateDelaySecs(delay_secs)
        self.validateUserMethod(heartbeat)

        log = self.logger
        while self.heartbeat_active:
            heartbeat()

            #delay_secs = delay_secs + VWorker.HEARTBEAT_DELTA + 100            

            log.info(json.dumps({'message' : 'Heartbeat just occurred, will delay %s' % delay_secs}))
            time.sleep(delay_secs);
        return

    '''
    def heartbeat(self):
        print 'heartbeat at %s' % (time.ctime(time.time()))
    '''

    def stop_heartbeat(self, heartbeat_thread):
        if heartbeat_thread is None:
            return
        self.heartbeat_active = False
        heartbeat_thread.join()

    def validateBool(self, var):
        if var is None:
            raise UnboundLocalError('var is None')
        elif not isinstance(var, bool):
            raise TypeError('var is not a bool')

    def validateDelaySecs(self, delay_secs):
        if delay_secs is None:
            raise UnboundLocalError('delay_secs is None')
        elif not isinstance(delay_secs, int):
            raise TypeError('delay_secs is not an int')
        elif delay_secs <= 0:
            raise TypeError('delay_secs must be > 0')

    def validateUserMethod(self, var):
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
