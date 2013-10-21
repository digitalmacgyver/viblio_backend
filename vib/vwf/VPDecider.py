#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import json
import mixpanel
import pprint
import time

# DEBUG - This is temporary until we reorganize popeye into vib.
import sys
sys.path.append( '../../popeye' )
from appconfig import AppConfig
config = AppConfig( '../../popeye/popeye' ).config()

mp = mixpanel.Mixpanel( config.mp_token )

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

class VPDecider( swf.Decider ):
    domain = vib.vwf.VPWorkflow.domain
    version = vib.vwf.VPWorkflow.version

    task_list = None

    def run( self ):
        print "Polling for events"

        # Listen for decisions in this task list.
        history = self.poll( task_list = 'VPDecider' + config.VPWSuffix )
        history_events = history.get( 'events', [] )
        while 'nextPageToken' in history:
            print "Getting next page of history."
            history = self.poll( next_page_token=history['nextPageToken'], task_list = 'VPDecider' + config.VPWSuffix )
            history_events += history.get( 'events', [] )

        print "Polling completed"

        if len( history_events ) == 0:
            print "Nothing to do."
            return True

        pprint.PrettyPrinter( indent=4 ).pprint( history_events )

        tasks = [ 'FaceDetect', 'FaceRecognize' ]

        workflow_input = _get_workflow_input( history_events )
        media_uuid = workflow_input['media_uuid']
        user_uuid = workflow_input['user_uuid']
        failed_tasks = _get_failed( history_events )
        timed_out_tasks = _get_timed_out_activities( history_events )
        completed_tasks = _get_completed( history_events )

        decisions = swf.Layer1Decisions()

        if _all_tasks_complete( tasks, completed_tasks ):
            # We are done.
            print "Workflow completed."
            _mp_log( "Workflow_Complete", media_uuid, user_uuid )
            decisions.complete_workflow_execution()
        else:
            # We are not done.  See if we can start anything or if we
            # are in an error state and need to terminate.
            for task in tasks:
                print "Evaluating %s" % task
                if task in completed_tasks:
                    print "Task %s already completed." % task
                elif task in failed_tasks:
                    details = failed_tasks[task]
                    # We hit a failure, see if we should restart a task.
                    print "Task %s has failed %d times, details were: %s" % ( task, len(details), details )
                    if len( details ) > VPW[task]['failure_retries']:
                        reason = "Task %s has exceeded maximum failure retries, terminating workflow." % task
                        print reason
                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_failed', 'activity': task, 'type' : 'max_retries' } )
                        decisions.fail_workflow_execution( reason=reason )
                    elif not details[-1].get( 'retry', False ):
                        reason = "Most recent failure for task %s said not to retry, terminating workflow." % task
                        print reason
                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task, 'type' : 'fatal_error' } )
                        decisions.fail_workflow_execution( reason=reason )
                    else:
                        print "Retrying task %s" % task

                        task_input = workflow_input
                        for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                            task_input[prerequisite] = input_opts

                        _mp_log( task+" Retry", media_uuid, user_uuid, { 'reason' : 'activity_failed', 'activity' : task } )
                        decisions.schedule_activity_task( 
                            task + '-' + workflow_input['media_uuid'],
                            task + config.VPWSuffix,
                            VPW[task]['version'],
                            task_list = VPW[task]['task_list'] + config.VPWSuffix,
                            input = json.dumps( task_input )
                            )

                elif task in timed_out_tasks:
                    details = timed_out_tasks[task]
                    # We hit a timeout, see if we should restart the
                    # task and if we should change the timeout values.
                    print "Task %s has timed out %d times, details were: %s" % ( task, len(details), details )
                    if len( details ) > len( VPW[task]['timeout_retries'] ):
                        reason = "Task %s has exceeded maximum timeout retries, terminating workflow." % task
                        print reason
                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task } )
                        decisions.fail_workflow_execution( reason=reason )
                    else:
                        print "Retrying task %s" % task

                        task_input = workflow_input
                        for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                            task_input[prerequisite] = input_opts

                        # Details is an array of all our past
                        # timeouts.  The N'th slot of the VPW
                        # configuration's timeout_retries lists how
                        # the N'th timeout should be handled with
                        # regard to extended timeouts.
                        timeout_factor = VPW[task]['timeout_retries'][ len( details )-1 ]
                        schedule_to_close_timeout = 'NONE'
                        schedule_to_start_timeout = 'NONE'
                        start_to_close_timeout    = 'NONE'
                        heartbeat_timeout         = 'NONE'
                        if VPW[task]['default_task_schedule_to_close_timeout'] != 'NONE':
                            schedule_to_close_timeout = str( timeout_factor * int( VPW[task]['default_task_schedule_to_close_timeout'] ) )
                        if VPW[task]['default_task_schedule_to_start_timeout'] != 'NONE':
                            schedule_to_start_timeout = str( timeout_factor * int( VPW[task]['default_task_schedule_to_start_timeout'] ) )
                        if VPW[task]['default_task_start_to_close_timeout'   ] != 'NONE':
                            start_to_close_timeout    = str( timeout_factor * int( VPW[task]['default_task_start_to_close_timeout'] ) )
                        if VPW[task]['default_task_heartbeat_timeout']         != 'NONE':
                            heartbeat_timeout         = str( timeout_factor * int( VPW[task]['default_task_heartbeat_timeout'] ) )

                        _mp_log( task + " Retry", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task } )
                        decisions.schedule_activity_task( 
                            task + '-' + workflow_input['media_uuid'],
                            task + config.VPWSuffix,
                            VPW[task]['version'],
                            task_list = VPW[task]['task_list'] + config.VPWSuffix,
                            input = json.dumps( task_input ),
                            schedule_to_close_timeout = schedule_to_close_timeout,
                            schedule_to_start_timeout = schedule_to_start_timeout,
                            start_to_close_timeout    = start_to_close_timeout,
                            heartbeat_timeout         = heartbeat_timeout
                            )

                elif _all_prerequisites_complete( task, completed_tasks ):
                    # We can start a new task.
                    print "Starting %s" % task

                    task_input = workflow_input
                    for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                        task_input[prerequisite] = input_opts

                    _mp_log( task + " Scheduled", media_uuid, user_uuid, { 'activity' : task } )
                    decisions.schedule_activity_task( 
                        task + '-' + workflow_input['media_uuid'],
                        task + config.VPWSuffix,
                        VPW[task]['version'],
                        task_list = VPW[task]['task_list'] + config.VPWSuffix,
                        input = json.dumps( task_input )
                        )
                else:
                    print "Can't start %s due to missing prerequisites." % task

        self.complete( decisions=decisions )
            
        return True

def _mp_log( event, media_uuid, user_uuid, properties = {} ):
    try:
        properties['$time'] = time.strftime( "%Y-%m-%dT%H:%M:%S", time.gmtime() )
        properties['user_uuid'] = user_uuid
        properties['deployment'] = config.mp_deployment

        mp.track( media_uuid, event, properties )
    except Exception as e:
        print "Error sending instrumentation ( %s, %s, %s ) to mixpanel: %s" % ( media_uuid, event, properties, e )

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
    '''Goes through a set of events and returns all the ActivityTasks
    which have been completed'''
    completed = {}
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) == 'ActivityTaskCompleted':
            completed_event = history_events[ event['activityTaskCompletedEventAttributes']['scheduledEventId'] - 1 ]
            if completed_event['eventType'] == 'ActivityTaskScheduled':
                completed_event_name =  completed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]

                completed[ completed_event_name ] = json.loads( event['activityTaskCompletedEventAttributes'].get( 'result', '{ "no_output" : true }' ) )
            else:
                raise Exception("AcivityTaskCompleted scheduled event attribute not an activity task!")
    
    return completed

def _get_failed( history_events ):
    '''Goes through a set of events and returns a hash of the failed
    ActivityTasks keyed on task name, with a value of the failure
    event's "details" attribute converted from JSON, or { "retry" :
    true } if there were no details.

    This does not include SWF timeouts.
    '''
    failed = {}
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) == 'ActivityTaskFailed':
            failed_event = history_events[ event['activityTaskFailedEventAttributes']['scheduledEventId'] - 1 ]
            if failed_event['eventType'] == 'ActivityTaskScheduled':
                failed_event_name = failed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
                details =  json.loads( event['activityTaskFailedEventAttributes'].get( 'details', '{ "retry" : true }' ) )
                if failed_event_name in failed:
                    failed[ failed_event_name ].append( details )
                else:
                    failed[ failed_event_name ] = [ details ]
            else:
                raise Exception("AcivityTaskFailed scheduled event attribute not an activity task!")            

    return failed

def _get_timed_out_activities( history_events ):
    '''Goes through a set of events and returns a hash of the timed
    out ActivityTasks keyed on task name, with a value of an array of
    the timeout's EventAttributes converted from JSON, which is a
    dictionary including the key timeoutType.

    This does not include decision timeouts.
    '''
    timed = {}
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) == 'ActivityTaskTimedOut':
            timed_event = history_events[ event['activityTaskTimedOutEventAttributes']['scheduledEventId'] - 1 ]
            if timed_event['eventType'] == 'ActivityTaskScheduled':
                timed_event_name = timed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
                details = event['activityTaskTimedOutEventAttributes']
                if timed_event_name in timed:
                    timed[ timed_event_name ].append( details )
                else:
                    timed[ timed_event_name ] = [ details ]
            else:
                raise Exception("AcivityTaskTimedOut scheduled event attribute not an activity task!")            
    return timed

def _any_failed_activities( history_events ):
    '''Goes through a set of events and returns true if we had an event of a sort of failure we deem to be fatal here.'''

    failure_types = {
        'ActivityTaskTimedOut' : True,
        'ActivityTaskFailed' : True
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
    '''Checks a given task against a list of completed tasks, and the specification provided by the VPWorkflow data structure.'''
    if task in VPW:
        for prerequisite in VPW[task]['prerequisites']:
            if prerequisite not in completed_tasks:
                return False
        return True
    else:
        raise Exception("Task %s not found in VPWorkflow data structure." % task )

def _get_input( task, completed_tasks ):
    '''Given a task, aggregate the outputs of its prerequisites from history events.'''
    task_input = {}
    for prerequisite in VPW[task]['prerequisites']:
        task_input[prerequisite] = completed_tasks.get( prerequisite, {} )
    return task_input
        
    

           
