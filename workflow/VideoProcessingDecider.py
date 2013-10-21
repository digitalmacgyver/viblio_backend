#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import pprint
import time

import VideoProcessingWorkflow
from VideoProcessingWorkflow import VPW

class VideoProcessingDecider( swf.Decider ):
    domain = VideoProcessingWorkflow.domain
    version = VideoProcessingWorkflow.version

    task_list = None

    def run( self ):
        print "Polling for events"

        # Listen for decisions in this task list.
        history = self.poll( task_list = 'VideoProcessingDecider' )
        history_events = history.get( 'events', [] )
        while 'nextPageToken' in history:
            print "Getting next page of history."
            history = self.poll( next_page_token=history['nextPageToken'], task_list = 'VideoProcessingDecider' )
            history_events += history.get( 'events', [] )

        print "Polling completed"

        if len( history_events ) == 0:
            print "Nothing to do."
            return True

        pprint.PrettyPrinter( indent=4 ).pprint( history_events )

        tasks = [ 'FaceDetect', 'FaceRecognize' ]

        workflow_input = _get_workflow_input( history_events )
        
        completed_tasks = _get_completed( history_events )

        decisions = swf.Layer1Decisions()

        if _all_tasks_complete( tasks, completed_tasks ):
            # We are done.
            print "Workflow completed."
            decisions.complete_workflow_execution()
        elif _any_failed_activities( history_events ):
            # We hit a failure or timeout, today do this simple thing
            # and kill the while workflow.
            print "Some task failed, failing this workflow."
            decisions.fail_workflow_execution( reason="At least one task failed" )
        else:
            # We are not done.  See if we can start anything.
            for task in tasks:
                print "Evaluating %s" % task
                if _all_prerequisites_complete( task, completed_tasks ):
                    # We can start a new task.
                    print "Starting %s" % task

                    task_input = {}
                    if len( VPW[task]['prerequisites'] ):
                        task_input = _get_input( task, completed_tasks )
                    else:
                        task_input = workflow_input

                    decisions.schedule_activity_task( 
                        task + '-' + workflow_input['media_uuid'],
                        task,
                        VPW[task]['version'],
                        task_list = VPW[task]['task_list'],
                        input = json.dumps( task_input )
                        )
                else:
                    print "Can't start %s due to missing prerequisites." % task

            self.complete( decisions=decisions )
            
        return True

def _get_workflow_input( history_events ):
    '''Return the original input to our workflow.'''
    for event in history_events:
        workflow_start_event = event.get( 'workflowExecutionStartedEventAttributes', False )
        if workflow_start_event:
            if 'input' not in workflow_start_event:
                raise Exception( "No input provided to workflow start event." )
            workflow_input = json.loads( workflow_start_event['input'] )
            if 'media_uuid' in workflow_input and 'user_uuid' in workflow_input:
                return workflow_input
            else:
                raise Exception( "Invalid workflow start event input, no media_uuid or user_uuid found in JSON" )
    raise Exception( "Could not find workflow start event!" )

def _get_completed( history_events ):
    '''Goes through a set of events and returns all the ActivityTasks which have been completed'''
    completed = {}
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) == 'ActivityTaskCompleted':
            completed_event = history_events[ event['activityTaskCompletedEventAttributes']['scheduledEventId'] - 1 ]
            if completed_event['eventType'] == 'ActivityTaskScheduled':
                completed[ completed_event['activityTaskScheduledEventAttributes']['activityType']['name'] ] = json.loads( event.get( 'result', '{ "no_output" : true }' ) )
            else:
                raise Exception("AcivityTaskCompleted scheduled event attribute not an activity task!")
    
    return completed

def _any_failed_activities( history_events ):
    '''Goes through a set of events and returns true if we had an event of a sort of failure we deem to be fatal here.'''

    failure_types = {
        'ActivityTaskTimedOut' : True,
        'ActivityTaskFailedEvent' : True
        }
    
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) in failure_types:
            return True
    return False

def _all_tasks_complete( tasks, completed_tasks ):
    '''If every task is a completed task return true, return false otherwise.'''
    for task in tasks:
        if task not in completed_tasks:
            return False
    return True

def _all_prerequisites_complete( task, completed_tasks ):
    '''Checks a given task against a list of completed tasks, and the specification provided by the VideoProcessingWorkflow data structure.'''
    if task in VPW:
        for prerequisite in VPW[task]['prerequisites']:
            if prerequisite not in completed_tasks:
                return False
        return True
    else:
        raise Exception("Task %s not found in VideoProcessingWorkflow data structure." % task )

def _get_input( task, completed_tasks ):
    '''Given a task, aggregate the outputs of its prerequisites from history events.'''
    task_input = {}
    for prerequisite in VPW[task]['prerequisites']:
        task_input[task] = completed_tasks.get( task, {} )
    return task_input
        
    

           
