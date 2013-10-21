#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

DOMAIN = vib.vwf.VPWorkflow.domain
VERSION = vib.vwf.VPWorkflow.version

# Register our domain.
d = swf.Domain( name=DOMAIN )
d.register()
print d.name, 'registered successfully'

# Register our workflow.
vp = swf.WorkflowType( 
    name    = 'VideoProcessing',
    domain  = DOMAIN, 
    version = VERSION
    )
vp.register(
    # Maximum default duration of the entire workflow in seconds - can
    # be overridden on a case by case basis.
    default_execution_start_to_close_timeout = str( 36*60*60 ),

    # Maximum default duration for a particular task - but in
    # particular this controls the timeouts for our decision tasks.
    # This should therefore be fairly breif.  The individual timeouts
    # for particular non-decision activities can be overridden both
    # with Activity Task defautls (set below) and at the time of
    # invocation.
    default_task_start_to_close_timeout = str( 5*60 ),

    # When we hit a timeout or explicitly terminate the items in this
    # workflow, terminate the child executions.
    default_child_policy = 'TERMINATE'
)
print vp.name, "successfully registered"

# Register our activities.
for activity, args in VPW.items():
    at = swf.ActivityType( 
        name      = activity, 
        domain    = args.get( 'domain'   , None ),
        version   = args.get( 'version'  , None )
        )
    at.register(
        task_list = args.get( 'task_list', None ),
        default_task_schedule_to_close_timeout = args.get( 'default_task_schedule_to_close_timeout', None ),
        default_task_start_to_close_timeout    = args.get( 'default_task_start_to_close_timeout'   , None ),
        default_task_heartbeat_timeout = args.get( 'default_task_heartbeat_timeout', None ),
        default_task_schedule_to_start_timeout = args.get( 'default_task_schedule_to_start_timeout', None )
        )
    print at.name, "registered successfully"
