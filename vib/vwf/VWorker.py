#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import mixpanel
import time

# DEBUG - This is temporary until we reorganize popeye into vib.
import sys
sys.path.append( '../../popeye' )
from appconfig import AppConfig
config = AppConfig( 'popeye', relpath='../../popeye/' ).config()

mp = mixpanel.Mixpanel( config.mp_token )

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

class VWorker( swf.ActivityWorker ):

    def __init__( self, **kwargs ):
        self.domain    = VPW[self.task_name].get( 'domain'   , None )
        self.task_list = VPW[self.task_name].get( 'task_list', '' ) + config.VPWSuffix
        self.version   = VPW[self.task_name].get( 'version'  , None )

        super( VWorker, self ).__init__( **kwargs )

    def run( self ):
        try:
            print "Starting run"

            activity_task = self.poll()

            if 'taskToken' not in activity_task or len( activity_task['taskToken'] ) == 0:
                print "Nothing to do"
                return True
            else:
                print "Running task."
                
                input_opts = json.loads( activity_task['input'] )

                media_uuid = input_opts['media_uuid']
                user_uuid  = input_opts['user_uuid']
                
                _mp_log( self.task_name + " Started", media_uuid, user_uuid, { 'activity' : self.task_name } )
                result = self.run_task( input_opts )

                if 'ACTIVITY_ERROR' in result:
                    print "Task had an error, failing the task with retry: %s" % result.get( 'retry', False ) 
                    _mp_log( self.task_name + " Failed", media_uuid, user_uuid, { 'activity' : self.task_name } )
                    self.fail( details = json.dumps( { 'retry' : result.get( 'retry', False ) } ) )
                else:
                    print "Task completed"
                    _mp_log( self.task_name + " Completed", media_uuid, user_uuid, { 'activity' : self.task_name } )

                    self.complete( result = json.dumps( result ) )

                return True

        except Exception as error:
            self.fail( reason = str( error ) )
            raise error

    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()


def _mp_log( event, media_uuid, user_uuid, properties = {} ):
    try:
        properties['$time'] = time.strftime( "%Y-%m-%dT%H:%M:%S", time.gmtime() )
        properties['user_uuid'] = user_uuid
        properties['deployment'] = config.mp_deployment

        mp.track( media_uuid, event, properties )
    except Exception as e:
        print "Error sending instrumentation ( %s, %s, %s ) to mixpanel: %s" % ( media_uuid, event, properties, e )
