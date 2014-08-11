#!/usr/bin/env python

import boto.sqs
from boto.sqs.message import RawMessage
import boto.swf
import boto.swf.layer2 as swf
import datetime
import json
import logging
import mixpanel
import pprint
import time

import vib.db.orm
from vib.db.models import * 

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.vwf.CheckerUtils as CheckerUtils

mp = mixpanel.Mixpanel( config.mp_token )
mp_web = mixpanel.Mixpanel( config.mp_web_token )

log = logging.getLogger( 'vib.vwf.VPDecider' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'vwf: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )
syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )

consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

class VPDecider( swf.Decider ):
    domain = vib.vwf.VPWorkflow.domain
    version = vib.vwf.VPWorkflow.version

    task_list = None

    def run( self ):
        try:
            return self.run_helper()
        except Exception as e:
            log.error( json.dumps( {
                        'message' : 'Exception during decision: %s' % e
                        } ) )
            raise

    def run_helper( self ):
        log.debug( json.dumps( {
                    'message' : 'Polling for events'
                    } ) )

        # Listen for decisions in this task list.
        history = self.poll( task_list = 'VPDecider' + config.VPWSuffix + config.UniqueTaskList )
        history_events = history.get( 'events', [] )
        while 'nextPageToken' in history:
            print "Getting next page of history."
            history = self.poll( next_page_token=history['nextPageToken'], task_list = 'VPDecider' + config.VPWSuffix + config.UniqueTaskList )
            history_events += history.get( 'events', [] )

        #with open('/tmp/pretty.history.' + str(time.time()) + '.txt', 'w') as f:
        #    pprint.PrettyPrinter( indent=4, stream=f ).pprint( history_events )
            
        if len( history_events ) == 0:
            log.debug( json.dumps( { 'message' : 'Nothing to do.' } ) )
            return True

        #pprint.PrettyPrinter( indent=4 ).pprint( history_events )

        tasks = [ 'Transcode', 'ActivityDetect', 'FaceDetect', 'FaceRecognize', 'NotifyComplete' ]

        workflow_input = _get_workflow_input( history_events )
        media_uuid = workflow_input['media_uuid']
        user_uuid = workflow_input['user_uuid']
        failed_tasks = _get_failed( history_events )
        no_lock_tasks = _get_failed_no_lock( history_events )
        timed_out_tasks = _get_timed_out_activities( history_events )
        completed_tasks = _get_completed( history_events )
        scheduled_tasks = _get_scheduled( history_events )
        most_recent_event = _get_most_recent( history_events )

        decisions = swf.Layer1Decisions()

        if _all_tasks_complete( tasks, completed_tasks ):
            # We are done.
            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Workflow for user %s video %s completed successfully." % ( user_uuid, media_uuid )
                        } ) )
            _mp_log( "Workflow_Complete", media_uuid, user_uuid, user_increment = { 'Video Completed' : 1 } )
            decisions.complete_workflow_execution()
            _update_media_status( media_uuid, 'WorkflowComplete', user_uuid )
        else:
            # We are not done.  See if we can start anything or if we
            # are in an error state and need to terminate.

            failed = False

            for task in tasks:
                if failed:
                    break
                print "Evaluating %s" % task
                if task in completed_tasks:
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'task' : task,
                                            'message' : "Task %s is completed." % task } ) )
                elif task in failed_tasks and most_recent_event[task] == 'failed':
                    details = failed_tasks[task]
                    # We hit a failure, see if we should restart a task.
                    log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                               'user_uuid' : user_uuid,
                                               'task' : task,
                                               'message' : "Task %s has failed %d times, details were: %s" % ( task, len(details), details ) } ) )

                    if len( details ) > VPW[task]['failure_retries']:
                        reason = "Task %s has exceeded maximum failure retries, terminating workflow." % task

                        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                                 'user_uuid' : user_uuid,
                                                 'task' : task,
                                                 'error_code' : 'max_failures',
                                                 'message' : reason } ) )

                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_failed', 'activity': task, 'type' : 'max_retries' } )

                        decisions.fail_workflow_execution( reason=reason[:250] )
                        failed = True
                        _update_media_status( media_uuid, 'WorkflowFailed', user_uuid, reason )

                    elif not details[-1].get( 'retry', False ):
                        reason = "Most recent failure for task %s said not to retry, terminating workflow." % task

                        log.error( json.dumps( {
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'task' : task,
                                    'error_code' : 'fatal_error',
                                    'message' : reason
                                    } ) )

                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task, 'type' : 'fatal_error' } )

                        decisions.fail_workflow_execution( reason=reason[:250] )
                        failed = True
                        _update_media_status( media_uuid, 'WorkflowFailed', user_uuid, reason )
                    else:

                        log.info( json.dumps( {
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'task' : task,
                                    'message' : "Retrying task %s" % task
                                    } ) )

                        task_input = workflow_input
                        for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                            task_input[prerequisite] = input_opts

                        if task in no_lock_tasks:
                            task_input['lock_wait'] = True

                        #_mp_log( task+" Retry", media_uuid, user_uuid, { 'reason' : 'activity_failed', 'activity' : task } )
                        schedule_to_close_timeout = VPW[task]['default_task_schedule_to_close_timeout'] 
                        schedule_to_start_timeout = VPW[task]['default_task_schedule_to_start_timeout'] 
                        start_to_close_timeout    = VPW[task]['default_task_start_to_close_timeout'] 
                        heartbeat_timeout         = VPW[task]['default_task_heartbeat_timeout'] 
                        log.info( json.dumps( { 'message' : 'setting heartbeat_timeout to %s' % heartbeat_timeout} ) )
                        decisions.schedule_activity_task( 
                            task + '-' + workflow_input['media_uuid'],
                            task + config.VPWSuffix,
                            VPW[task]['version'],
                            task_list = VPW[task]['task_list'] + config.VPWSuffix + config.UniqueTaskList,
                            input = json.dumps( task_input ),
                            schedule_to_close_timeout = schedule_to_close_timeout,
                            schedule_to_start_timeout = schedule_to_start_timeout,
                            start_to_close_timeout    = start_to_close_timeout,
                            heartbeat_timeout         = heartbeat_timeout
                            )

                elif task in no_lock_tasks and most_recent_event[task] == 'no_lock':
                    failed = self.process_no_lock_tasks(task, no_lock_tasks, completed_tasks, decisions, media_uuid, user_uuid, workflow_input, config)
                elif task in timed_out_tasks and most_recent_event[task] == 'timed_out':
                    details = timed_out_tasks[task]
                    # We hit a timeout, see if we should restart the
                    # task and if we should change the timeout values.

                    if len( details ) > len( VPW[task]['timeout_retries'] ):
                        reason = "Task %s has timed out %d times exceeding the maximum allowed timeouts of %d, details were: %s" % ( task, len(details), len( VPW[task]['timeout_retries'] ), details )

                        log.error( json.dumps( {
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'task' : task,
                                    'error_code' : 'max_timeouts',
                                    'message' : reason
                                    } ) )

                        _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task } )
                        decisions.fail_workflow_execution( reason=reason[:250] )
                        failed = True
                        _update_media_status( media_uuid, 'WorkflowFailed', user_uuid, reason )
                    else:
                        log.warning( json.dumps( {
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'task' : task,
                                    'message' : "Retrying task %s has timed out %d times of a maximum allowed timeouts of %d, details were: %s" % ( task, len(details), len( VPW[task]['timeout_retries'] ), details )
                                    } ) )

                        task_input = workflow_input
                        for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                            task_input[prerequisite] = input_opts

                        if task in no_lock_tasks:
                            task_input['lock_wait'] = True

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
                        #_mp_log( task + " Retry", media_uuid, user_uuid, { 'reason' : 'activity_timeout', 'activity' : task } )
                        log.info( json.dumps( { 'message' : 'setting heartbeat_timeout to %s' % heartbeat_timeout} ) )
                        decisions.schedule_activity_task( 
                            task + '-' + workflow_input['media_uuid'],
                            task + config.VPWSuffix,
                            VPW[task]['version'],
                            task_list = VPW[task]['task_list'] + config.VPWSuffix + config.UniqueTaskList,
                            input = json.dumps( task_input ),
                            schedule_to_close_timeout = schedule_to_close_timeout,
                            schedule_to_start_timeout = schedule_to_start_timeout,
                            start_to_close_timeout    = start_to_close_timeout,
                            heartbeat_timeout         = heartbeat_timeout
                            )

                elif _all_prerequisites_complete( task, completed_tasks ) and task not in scheduled_tasks:
                    # We can start a new task.
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'task' : task,
                                            'message' : "Starting %s for the first time" % task } ) )

                    task_input = workflow_input
                    for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                        task_input[prerequisite] = input_opts

                    #_mp_log( task + " Scheduled", media_uuid, user_uuid, { 'activity' : task } )
                    schedule_to_close_timeout = VPW[task]['default_task_schedule_to_close_timeout'] 
                    schedule_to_start_timeout = VPW[task]['default_task_schedule_to_start_timeout'] 
                    start_to_close_timeout    = VPW[task]['default_task_start_to_close_timeout'] 
                    heartbeat_timeout         = VPW[task]['default_task_heartbeat_timeout'] 
                    log.info( json.dumps( { 'message' : 'setting heartbeat_timeout to %s' % heartbeat_timeout} ) )
                    decisions.schedule_activity_task( 
                        task + '-' + workflow_input['media_uuid'],
                        task + config.VPWSuffix,
                        VPW[task]['version'],
                        task_list = VPW[task]['task_list'] + config.VPWSuffix + config.UniqueTaskList,
                        input = json.dumps( task_input ),
                        schedule_to_close_timeout = schedule_to_close_timeout,
                        schedule_to_start_timeout = schedule_to_start_timeout,
                        start_to_close_timeout    = start_to_close_timeout,
                        heartbeat_timeout         = heartbeat_timeout
                        )
                elif task in scheduled_tasks:
                    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                             'user_uuid' : user_uuid,
                                             'task' : task,
                                             'message' : "%s has already been scheduled and is pending." % task } ) )                    
                else:
                    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                             'user_uuid' : user_uuid,
                                             'task' : task,
                                             'message' : "Can't start %s due to missing prerequisites." % task } ) )

        self.complete( decisions=decisions )
            
        return True

    def process_no_lock_tasks(self, task, no_lock_tasks, completed_tasks, decisions, media_uuid, user_uuid, workflow_input, config):
        CheckerUtils.validate_string(task)
        CheckerUtils.validate_dict(no_lock_tasks)
        CheckerUtils.validate_dict(completed_tasks)
        CheckerUtils.validate_object(decisions)
        CheckerUtils.validate_string(media_uuid)
        CheckerUtils.validate_string(user_uuid)
        CheckerUtils.validate_object(workflow_input)
        CheckerUtils.validate_object(config)

        log.info( json.dumps({'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'task' : task, 'message' : "Retrying task %s" % task}))
        details = no_lock_tasks[task]
        if len(details) > VPW[task]['lock_retries']:
            reason = 'Task %s has exceeded maximum lock retries, terminating workflow' % task
            log.error( json.dumps({'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'task' : task, 'error_code' : 'max_timeouts', 'message' : reason}))
            _mp_log( "Workflow Failed", media_uuid, user_uuid, { 'reason' : 'no_lock retries exceeded', 'activity' : task, 'type' : 'fatal_error' } )
            decisions.fail_workflow_execution(reason = reason[:250])
            _update_media_status( media_uuid, 'WorkflowFailed', user_uuid, reason )
            return True
        else:
            message = 'Retrying task %s for time %d out of %d allowed lock retries' % (task, len(details), VPW[task]['lock_retries'])
            log.warning( json.dumps({'media_uuid' : media_uuid, 'user_uuid' : user_uuid, 'task' : task, 'message' : message}))
            task_input = workflow_input
            for prerequisite, input_opts in  _get_input( task, completed_tasks ).items():
                task_input[prerequisite] = input_opts
            task_input['lock_wait'] = True
            schedule_to_close_timeout = VPW[task]['default_task_schedule_to_close_timeout'] 
            schedule_to_start_timeout = VPW[task]['default_task_schedule_to_start_timeout'] 
            start_to_close_timeout    = VPW[task]['default_task_start_to_close_timeout'] 
            heartbeat_timeout         = VPW[task]['default_task_heartbeat_timeout'] 
            decisions.schedule_activity_task( 
                task + '-' + workflow_input['media_uuid'],
                task + config.VPWSuffix,
                VPW[task]['version'],
                task_list = VPW[task]['task_list'] + config.VPWSuffix + config.UniqueTaskList,
                input = json.dumps( task_input ),
                schedule_to_close_timeout = schedule_to_close_timeout,
                schedule_to_start_timeout = schedule_to_start_timeout,
                start_to_close_timeout    = start_to_close_timeout,
                heartbeat_timeout         = heartbeat_timeout
                )
            return False
    
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

def _get_most_recent( history_events ):
    '''Returns an arrah keyed off of Activity Task name with a value
    of the most recent event for that activity task, which could be
    one of:
    * scheduled
    * completed
    * timed_out
    * no_lock
    * failed'''
    most_recent_event_ids = {}
    most_recent_events = {}

    for event in history_events:
        event_id = event['eventId']
        event_name = event.get( 'eventType', 'Unknown' )
        if event_name == 'ActivityTaskScheduled':
            scheduled_event_name =  event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
            if scheduled_event_name not in most_recent_events or most_recent_event_ids[scheduled_event_name] < event_id:
                most_recent_events[scheduled_event_name] = 'scheduled'
                most_recent_event_ids[scheduled_event_name] = event_id

        elif event_name == 'ActivityTaskCompleted':
            completed_event = history_events[ event['activityTaskCompletedEventAttributes']['scheduledEventId'] - 1 ]
            if completed_event['eventType'] == 'ActivityTaskScheduled':
                completed_event_name =  completed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
                if completed_event_name not in most_recent_events or most_recent_event_ids[completed_event_name] < event_id:
                    most_recent_events[completed_event_name] = 'completed'
                    most_recent_event_ids[completed_event_name] = event_id
                    
        elif event_name == 'ActivityTaskFailed':
            failed_event = history_events[ event['activityTaskFailedEventAttributes']['scheduledEventId'] - 1 ]
            if failed_event['eventType'] == 'ActivityTaskScheduled':
                failed_event_name = failed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
                reason = event['activityTaskFailedEventAttributes'].get( 'reason' )
                if reason == 'no_lock':
                    event_type = 'no_lock'
                else:
                    event_type = 'failed'
                if failed_event_name not in most_recent_events or most_recent_event_ids[failed_event_name] < event_id:
                    most_recent_events[failed_event_name] = event_type
                    most_recent_event_ids[failed_event_name] = event_id
                    
        elif event_name == 'ActivityTaskTimedOut':
            timed_event = history_events[ event['activityTaskTimedOutEventAttributes']['scheduledEventId'] - 1 ]
            if timed_event['eventType'] == 'ActivityTaskScheduled':
                timed_event_name = timed_event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]
                if timed_event_name not in most_recent_events or most_recent_event_ids[timed_event_name] < event_id:
                    most_recent_events[timed_event_name] = 'timed_out'
                    most_recent_event_ids[timed_event_name] = event_id

    return most_recent_events
    

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

def _get_scheduled( history_events ):
    '''Goes through a set of events and returns all the ActivityTasks
    which have been scheduled prior to this decision'''
    scheduled = {}
    for event in history_events:
        if event.get( 'eventType', 'Unknown' ) == 'ActivityTaskScheduled':
            scheduled_event_name =  event['activityTaskScheduledEventAttributes']['activityType']['name'][:-len( config.VPWSuffix )]

            scheduled[ scheduled_event_name ] = True
    
    return scheduled


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
                #reason = json.loads( event['activityTaskFailedEventAttributes'].get( 'reason' ))
                reason = event['activityTaskFailedEventAttributes'].get( 'reason' )
                if reason == 'no_lock':
                    continue
                details =  json.loads( event['activityTaskFailedEventAttributes'].get( 'details', '{ "retry" : true }' ) )
                if failed_event_name in failed:
                    failed[ failed_event_name ].append( details )
                else:
                    failed[ failed_event_name ] = [ details ]
            else:
                raise Exception("AcivityTaskFailed scheduled event attribute not an activity task!")            

    return failed

def _get_failed_no_lock( history_events ):
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
                #reason = json.loads( event['activityTaskFailedEventAttributes'].get( 'reason' ))
                reason = event['activityTaskFailedEventAttributes'].get( 'reason' )
                if reason is None or reason != 'no_lock':
                    continue
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
        
def _update_media_status( media_uuid, status, user_uuid, reason="Unknown" ):
    orm = vib.db.orm.get_session()
    try:
        orm.commit()
    except Exception as e:
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'user_uuid' : user_uuid,
                                 'message' : "Failed to pre-commit orm for media status to %s for media_uuid %s, error was: %s" % ( status, media_uuid, e ) } ) )
        orm.rollback()

    try:
        media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

        if status == 'WorkflowComplete':
            media.status = 'complete'
        elif status == 'WorkflowFailed':
            # If the video is already visible and we've had a failure,
            # leave it as visible, otherwise set it to failed.
            if media.status is not None and media.status != 'visible':
                media.status = 'failed'
            
        mwfs = MediaWorkflowStages( workflow_stage = status )
        media.media_workflow_stages.append( mwfs )
        
        orm.commit()

    except Exception as e:
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'user_uuid' : user_uuid,
                                 'message' : "Failed to update media status to %s for media_uuid %s, error was: %s" % ( status, media_uuid, e ) } ) )

    # Now send an email if there was a problem.
    if ( status == 'WorkflowFailed' ):
        body = ''
        try:
            user_id = 'Unknown'
            user_email = 'Unknown'
            filename = 'Unknown'
            title = 'Unknown'
            media_id = 'Unknown'
            workflow_stages = "Workflow Stage\t\tCreated Date\n"
            try:
                user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()
                user_id = user.id
                user_email = user.email
            except Exception as ue:
                pass
            try:
                media_id = media.id
                filename = media.filename
                title = media.title
            except Exception as me:
                pass
            try:
                workflow_stage_list = orm.query( MediaWorkflowStages ).filter( MediaWorkflowStages.media_id == media_id ).order_by( MediaWorkflowStages.created_date )[:]
                for ws in workflow_stage_list:
                    workflow_stages += "%s\t\t%s\n" % ( ws.workflow_stage, ws.created_date )
            except Exception as we:
                pass

            loggly_errors = "https://viblio.loggly.com/search#terms=json.level%%3A%%22ERROR%%22%%20AND%%20json.name%%3A%%22vib.vwf*%%22%%20AND%%20json.activity_log.media_uuid%%3A%%22%s%%22&from=%s&until=%s&source_group=" % ( 
                media_uuid, 
                ( datetime.datetime.utcnow() - datetime.timedelta( days=3 ) ).strftime( "%Y-%m-%dT%H:%M:%SZ" ).replace( ":", "%3A" ),
                ( datetime.datetime.utcnow() + datetime.timedelta( hours=3 ) ).strftime( "%Y-%m-%dT%H:%M:%SZ" ).replace( ":", "%3A" ) )

            loggly_events = "https://viblio.loggly.com/search#terms=json.activity_log.media_uuid%%3A%%22%s%%22&from=%s&until=%s&source_group=" % ( 
                media_uuid, 
                ( datetime.datetime.utcnow() - datetime.timedelta( days=3 ) ).strftime( "%Y-%m-%dT%H:%M:%SZ" ).replace( ":", "%3A" ),
                ( datetime.datetime.utcnow() + datetime.timedelta( hours=3 ) ).strftime( "%Y-%m-%dT%H:%M:%SZ" ).replace( ":", "%3A" ) )
            
            subject = "%s VWF Failure" % ( config.VPWSuffix )
            if media.status == 'visible':
                subject += " but visible: "
            else:
                subject += ": "
            subject += "'%s', %s, %s" % ( title[:20], user_email, reason )

            body = '''
<body>
<pre>
deployment      : %s
user_uuid / id  : %s / %s
user_email      : %s
filename        : %s
title           : %s
media_uuid / id : %s / %s

reason          :
=================
%s


Workflow stage history:
=======================
%s
</pre>
<p>
Error messages:<br />
<a href="%s">%s</a>
</p>
<p>
Event history:<br />
<a href="%s">%s</a>
</p>
<pre>
Download reproducer:

cd ~/video_processor/vib
source setup-env.sh
cd utils
python -i s3.py
download_file( '/wintmp/problems/%s', '%s', '%s/%s' )
</pre>

</body>
''' % ( config.VPWSuffix, user_uuid, user_id, user_email, filename, title, media_uuid, media_id, reason, workflow_stages, loggly_errors, loggly_errors, loggly_events, loggly_events, filename, config.bucket_name, media_uuid, media_uuid )

            connection = boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )
            queue = connection.get_queue( config.email_queue )
            message = RawMessage()
            message.set_body( json.dumps( {
                        'subject' : subject,
                        'to' : [ { 'email' : 'admin@viblio.com', 'name' : 'Viblio Administrator' } ],
                        'body' : body
                        } ) )
            queue.write( message )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Failed to send email error for media_uuid %s, message was: %s, error was: %s" % ( media_uuid, body, e ) } ) )

    return

           
