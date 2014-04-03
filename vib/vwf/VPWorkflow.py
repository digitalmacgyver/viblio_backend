# The configuration of the items in our workflow.  This is used
# multiple locations.

# It is used to register things in the first place, and it is used in
# our Decider to determine when it is safe to initiate the next steps.

# Steps are started when all prerequisite steps have completed.

# Note, there is a balance in setting the timeouts:
# Long timeouts mean when a component has failed, the retry will wait
# a long time.
#
# Short timeouts mean an outage of a dependent service of that
# duration will trigger a failure - for example if a third party web
# service is down for an hour, and our timeout is 10 minutes we will
# fail bunches of jobs that could have just waited.
# 
# We'll err on the side of timeouts that are too short so we don't
# wait to retry broken things that could be better now.

# NOTE: To conform with certain other conding assumptions:
# lock_heartbeat_secs*3 should be less than lock_wait_secs
# lock_wait_secs should be a bit longer than the
# default_task_heartbeat_timeout, if any

domain = 'Viblio'
version = '1.0.7'

VPW = {

    'Upload' : {
        'name'            : 'Upload',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'UploadTask',
        'prerequisites'   : [],
        'failure_retries' : 1,
        'timeout_retries' : [1, 2, 4],
        'default_task_schedule_to_close_timeout' : str( 21*60 ),
        'default_task_schedule_to_start_timeout' : str( 21*60 ),
        'default_task_start_to_close_timeout' : str( 20*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 300
        },

    'Transcode' : {
        'name'            : 'Transcode',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'TranscodeTask',
        # Someday this will be true.
        # 'prerequisites'   : [ 'Upload' ],
        'prerequisites'   : [],
        'failure_retries' : 1,
        'timeout_retries' : [1, 2, 4],
        'default_task_schedule_to_close_timeout' : str( 15*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60*60 ),
        'default_task_start_to_close_timeout' : str( 10*60*60 ),
        'default_task_heartbeat_timeout' : str( 300 ),
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 330
        },

    'ActivityDetect' : {
        'name'            : 'ActivityDetect',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'ActivityDetectTask',
        # Should be just transcode, but current bugs require it to be FD.
        #'prerequisites'   : [ 'Transcode', 'FaceDetect' ],
        'prerequisites'   : [ 'Transcode' ],
        'failure_retries' : 1,
        'timeout_retries' : [1, 2, 4],
        'default_task_schedule_to_close_timeout' : str( 15*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60*60),
        'default_task_start_to_close_timeout' : str( 10*60*60 ),
        'default_task_heartbeat_timeout' : str( 300 ),
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 330
        },

    'FaceDetect' : {
        'name'            : 'FaceDetect',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'FaceDetectTask',
        'prerequisites'   : [ 'Transcode' ],
        'failure_retries' : 3,
        'timeout_retries' : [1, 2, 4],
        'default_task_schedule_to_close_timeout' : str( 15*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60*60),
        'default_task_start_to_close_timeout' : str( 10*60*60 ),
        'default_task_heartbeat_timeout' : str( 300 ),
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 330
        },

    'FaceRecognize' : {
        'name'            : 'FaceRecognize',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'FaceRecognizeTask',
        'prerequisites'   : [ 'FaceDetect' ],
        # Lots of things could go wrong in Face Recognize, so we'll
        # give it several attempts.
        'failure_retries' : 5,
        # This is sort of ugly - we want to retry on heartbeat timeout
        # until we run out of time completely.  We allow this job to
        # run to 36 hours, with a 5 minute timeout.  So... up to 432
        # retries it is!
        'timeout_retries' : [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        'default_task_schedule_to_close_timeout' : str( 36*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 36*60*60 ),
        'default_task_start_to_close_timeout' : str( 36*60*60 ),
        'default_task_heartbeat_timeout' : str( 5*60 ),
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 330
        },

    'NotifyComplete' : {
        'name'            : 'NotifyComplete',
        'domain'          : domain,
        'version'         : version,
        'task_list'       : 'NotifyCompleteTask',
        'prerequisites'   : [ 'FaceRecognize', 'ActivityDetect' ],
        'failure_retries' : 2,
        'timeout_retries' : [1, 2, 4],
        'default_task_schedule_to_close_timeout' : str( 15*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60 ),
        'default_task_start_to_close_timeout'    : str( 5*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        'lock_retries' : 2,
        'lock_heartbeat_secs' : 90,
        'lock_wait_secs' : 330
       },
}
