#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import time

import VideoProcessingWorkflow
from VideoProcessingWorkflow import VPW

class VideoProcessingDecider( swf.Decider ):
    domain = VideoProcessingWorkflow.domain
    version = VideoProcessingWorkflow.version

    task_list = None

    def run( self ):
        print "Polling for events"

        history = self.poll( task_list = 'VideoProcessingDecider' )
        
        print "Polling completed"

        # Make helpers to iterate over all events and determine if a
        # given VPW is ready to go.

        if 'events' in history:
            workflow_events = [e for e in history['events'] if not e['eventType'].startswith( 'Decision' )]

            last_event = workflow_events[-1]
            decisions = swf.Layer1Decisions()

            if last_event['eventType'] == 'WorkflowExecutionStarted':
                print "Starting Upload Task"
                decisions.schedule_activity_task( 
                    'activity id, an arbitrary string', 
                    'Upload', # The Activity Type - must be a reigstered type
                    '1.0.2', # The activity version.
                    task_list = 'UploadTask', # The Activity task list
                    heartbeat_timeout = str( 900 ), # Override
                    schedule_to_close_timeout = None, # Override
                    schedule_to_start_timeout = str( 900 ), # Override
                    start_to_close_timeout = None, # Override
                    control = None, # 32 kb string not sent to task, but available to the decider in the future.
                    input = json.dumps( { 'arbitrary' : ['string', 'we', 'use', 'json'] } )
                    )
            elif last_event['eventType'] == 'ActivityTaskCompleted':
                # DEBUG - this doesn't handle paging, we could get
                # there if we have something down for a long time with
                # lots of retries.
                last_event_attrs = last_event['activityTaskCompletedEventAttributes']
                completed_activity_id = last_event_attrs['scheduledEventId'] - 1

                activity_data = history['events'][completed_activity_id]
                activity_attrs = activity_data['activityTaskScheduledEventAttributes']
                activity_name = activity_attrs['activityType']['name']

                result = last_event['activityTaskCompletedEventAttributes'].get( 'result' )

                print "Activity %s completed with result %s" % ( activity_name, result )

                if activity_name == 'stageA2':
                    print "Starting task_B2, task_C2"
                    decisions.schedule_activity_task( '%s-%i' % ( 'stageB2', time.time() ), 'stageB2', self.version, task_list='task_B2', input=result )
                    decisions.schedule_activity_task( '%s-%i' % ( 'stageC2', time.time() ), 'stageC2', self.version, task_list='task_C2', input=result )
                else:
                    decisions.complete_workflow_execution()
                    
            self.complete( decisions=decisions )
            
        return True




           
