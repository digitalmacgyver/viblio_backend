#!/usr/bin/env python

import os
os.environ['BOTO_CONFIG'] = os.path.dirname( __file__ ) + '../config/boto.config'
from optparse import OptionParser
import sys

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

from vib.thirdParty.mturkcore import MechanicalTurk

def get_outstanding_assignments():
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            'aws_key'     : config.awsAccess,
            'aws_secret_key' : config.awsSecret
            }  )
    
    options = { 
        'Statistic' : 'NumberAssignmentsAvailable', 
        'TimePeriod' : 'LifeToDate' 
        }

    result = mt.create_request( 'GetRequesterStatistic', options )

    assignments = mt.get_response_element( 'LongValue', result )
    
    if assignments == None:
        assignments = 0
    else:
        assignments = int( assignments )

    print "There are : %s assignments available." % assignments
    return assignments

def notify_workers( workers, assignments ):
    ret = True

    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            'aws_key'     : config.awsAccess,
            'aws_secret_key' : config.awsSecret
            }  )
    
    max_workers_per_notification = 99
    for idx in range( 0, len( workers ), max_workers_per_notification ):
        worker_list = workers[idx:idx+max_workers_per_notification]

        task_url = 'https://workersandbox.mturk.com/mturk/searchbar?selectedSearchType=hitgroups&searchWords=oilbiv&minReward=0.00&x=15&y=17'

        options = { 
            'Subject' : 'Pending Face Recognition Tasks', 
            'MessageText' : "There are %d face recognition tasks pending at:\n\n%s\n" % ( assignments, task_url ),
            'WorkerId' : worker_list
            }

        result = mt.create_request( 'NotifyWorkers', options )
        is_valid = 'NotifyWorkersFailureStatus' not in result['NotifyWorkersResponse']['NotifyWorkersResult']
        if not is_valid:
            print "Failed to notify some subset of workers: %s" % workers[idx:idx+max_workers_per_notification]
            ret = False

    return ret

if __name__ == '__main__':
    # For the beta, we manually maintain a list of workers here.  

    # We can't add a worker to notification until they have done at
    # least one task for us.
    workers = [
        'A3NNF2DM3T5FFQ', # Matt Hayward
        'ANT1E8VYCK300', # Bidyut Parruck
        'A2UAN9XAD1587R', # video-analytics-inc.com
        'A3T5PC3TPU8MXW', # Mona?
        'A340CISQI4UAJQ', # Ramsri
        'A1NQ1J6ZCVSP7P', # Jason
        'A2PA1XJK46N3IR', # Ilya
        #'A6HPE96M56JT4', # elance worker
        ]

    print "Checking if there are pending notifications."
    count = 0
    try:
        count = get_outstanding_assignments()
    except Exception as e:
        print "Failed to get assignment count, error was: %s" % e
        raise
       
    try:
        if count > 0:
            if notify_workers( workers, count ):
                print "Successfully notified all workers: %s" % workers
            else:
                print "Failed to notify some workers."
    except Exception as e:
        print "Failed to notify workers, error was: %s" % e
        raise
