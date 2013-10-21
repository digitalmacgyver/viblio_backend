#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import time

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

class VWorker( swf.ActivityWorker ):

    def __init__( self, **kwargs ):
        self.domain    = VPW[self.task_name].get( 'domain'   , None )
        self.task_list = VPW[self.task_name].get( 'task_list', None )
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
                result = self.run_task( json.loads( activity_task['input'] ) )
                
                if 'ACTIVITY_ERROR' in result:
                    print "Task had an error, failing the task with retry: %s" % result.get( 'retry', False ) 
                    self.fail( details = json.dumps( { 'retry' : result.get( 'retry', False ) } ) )
                else:
                    print "Task completed"
                    self.complete( result = json.dumps( result ) )

                return True

        except Exception as error:
            self.fail( reason = str( error ) )
            raise error

    def run_task( self, opts ):
        '''Clients must override this method'''
        raise NotImplementedError()
