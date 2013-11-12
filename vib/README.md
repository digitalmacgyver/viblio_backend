vib
===============

The root of our back end video processing Python repository.  Includes
multiple utilities, applications, and configuration elements.

Running Code in the Repository
------------------------------

Code in the repository typically requires that PYTHONPATH include the
parent of the vib directory, and certain elements require the
BOTO_CONFIG environment variable to be set.

To establish these environment variables:
```
cd video_processor/vib
source setup-env.sh
```

Main Modules
------------

* [config](./config/README.md) - Holds the configuration module, and configuration files, used by the various utilities and programs in vib
* [db](./db/README.md) - The [SQLAlchemy](http://www.sqlalchemy.org/) based database interaction module for interacting with [our database](../schema/README.md)
* [vwf](./vwf/README.md) - The Video Workflow pipeline that processes our videos once [Popeye](../popeye/README.md) initiates the workflow
  * There are several subcomponents of [vwf](./vwf/README.md)


Minor Modules
-------------

* [fb](./fb/README.md) - Module for Facebook interaction, presently only used to import Facebook contacts and tagged photos of a user and their friends
* [rekog](./rekog/README.md) - Module for interaction with [ReKognition](http://www.rekognition.com/), a web service that performs face recognition
* [thirdParty](./thirdParty/README.md) - Module for installing third party code and tools
* [utils](./utils/README.md) - Module for utility scripts and code used by multiple applications (e.g. S3 interaction code, our Serialization module)

Adding New Programs
===================

There are some conventions for applications added to the vib
repository.

Configuration
-------------

Ensure your application loads and uses the configuration as described
in the Deployment Conventions section of the [configuration
documentation](./config/README.md)

Logging
-------

Many of the applications here log to the
[Loggly](https://viblio.loggly.com/dashboards) service. Loggly allows
us to consolidate logs to a central location, search and filter them,
and set up alerts on various events.

If you would like to log to Loggly, first configure your machine to
send syslog files to Loggly (this has already been done on all the
relevant Viblio servers in EC2):

```
wget -q -O - https://www.loggly.com/install/configure-syslog.py | sudo python - install --auth 32c3f593-612f-4f75-81e6-8f253573c95d --subdomain viblio
sudo /etc/init.d/rsyslog restart
```

Then prepend this to the beginning of your program to log to both
Loggly and the console:

```
import json
import logging

log = logging.getLogger( 'vib.your.module' ) # FILL IN YOUR MODULE NAME
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

# THIS LINE REQUIRES YOU TO HAVE PREVIOUSLY SET UP THE config VARIABLE
#  AS DESCRIBED IN THE PRIOR CONFIGURATION SECTION
format_string = 'rescue_orphan_faces: { "name" : "%(name)s", "module" : "%(modul
e)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(leveln
ame)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s 
}'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )
```

***NOTE:*** 
By convention, our log messages are formatted as JSON, this allows
Loggly to do much better searching and organization of our log files.

Whenever possible, if the user_uuid, or media_uuid is a relevant
concept for the log message, it should be provided as a element of the
message.

Then log messages by calling:
```
log.debug( json.dumps( {
	   'user_uuid' : user_uuid,
	   'message'   : "debug message"
	   } ) )

log.info( json.dumps( {
	  'media_uuid' : media_uuid,
	  'message' : "informational message"
	  } ) )

log.warning( json.dumps( {
           'arbitrary_field_of_interest' : field.data,
	   'message' : "warning message"
	   } ) )

log.error( json.dumps( {
           'arbitrary_structure' : { 
               'with_nested_fields' : 'blah',
               'or_arrays' : [ 1, 2, 'foo' ]
           },
	   'message' : "error message"
	   } ) )
```






