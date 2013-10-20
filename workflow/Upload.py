#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import time

import VideoProcessingWorkflow
from VideoProcessingWorkflow import VPW

class_name = 'Upload'

class Upload( swf.ActivityWorker ):
    domain    = VPW[class_name].get( 'domain'   , None )
    task_list = VPW[class_name].get( 'task_list', None )
    version   = VPW[class_name].get( 'version'  , None )

    def run( self ):
        try:
            print "Calling run for %s" % type( self )

            activity_task = self.poll()

            print "Activity_task type %s" % type( activity_task )
        
            for k, v in activity_task.items():
                print "Key: %s, Value %s" % ( k, v )
                print

            print "Sleeping for 5 seconds"
            time.sleep( 5 )

            self.complete( result = json.dumps( [ 'we', 'also', 'return json' ] ) )

        except Exception as error:
            self.fail( reason = str( error ) )
            raise error

        return True
