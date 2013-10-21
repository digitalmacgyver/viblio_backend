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

domain = 'Viblio'
version = '1.0.4'

VPW = {

    'Upload' : {
        'name'          : 'Upload',
        'domain'        : domain,
        'version'       : version,
        'task_list'     : 'UploadTask',
        'prerequisites' : [],
        'default_task_schedule_to_close_timeout' : str( 21*60 ),
        'default_task_schedule_to_start_timeout' : str( 21*60 ),
        'default_task_start_to_close_timeout' : str( 20*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        },

    'Transcode' : {
        'name'          : 'Transcode',
        'domain'        : domain,
        'version'       : version,
        'task_list'     : 'TranscodeTask',
        'prerequisites' : [ 'Upload' ],
        'default_task_schedule_to_close_timeout' : str( 15*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60*60 ),
        'default_task_start_to_close_timeout' : str( 10*60*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        },

    'FaceDetect' : {
        'name'          : 'FaceDetect',
        'domain'        : domain,
        'version'       : version,
        'task_list'     : 'FaceDetectTask',
        # For the time being, everything above FaceDetect happens out
        # of this workflow, so FaceDetect is an entry point into the
        # existing workflow.
        'prerequisites' : [] ,
        'default_task_schedule_to_close_timeout' : str( 15*60*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60*60),
        'default_task_start_to_close_timeout' : str( 10*60*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        },

    'FaceRecognize' : {
        'name'          : 'FaceRecognize',
        'domain'        : domain,
        'version'       : version,
        'task_list'     : 'FaceRecognizeTask',
        'prerequisites' : [ 'FaceDetect' ],
        'default_task_schedule_to_close_timeout' : str( 30*60 ),
        'default_task_schedule_to_start_timeout' : str( 30*60 ),
        'default_task_start_to_close_timeout' : str( 20*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        },

    'NotifyComplete' : {
        'name'          : 'NotifyComplete',
        'domain'        : domain,
        'version'       : version,
        'task_list'     : 'NotifyCompleteTask',
        'prerequisites' : [ 'FaceRecognize' ],
        'default_task_schedule_to_close_timeout' : str( 15*60 ),
        'default_task_schedule_to_start_timeout' : str( 15*60 ),
        'default_task_start_to_close_timeout'    : str( 5*60 ),
        'default_task_heartbeat_timeout' : 'NONE',
        },

}
