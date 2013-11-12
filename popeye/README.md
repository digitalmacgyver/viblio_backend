popeye
======

Popeye is the legacy video processing pipeline.  Popeye is a web
service run under Apache on our production servers, and under the
Python web module in local testing environments.  Popeye is a
multi-threaded application and new threads are spawned for each
request calling Worker.run().

Currently its scope is limited to:

* Receiving notification from Brewtus that an upload is complete
* Copying the original file to S3
* Creating a record of this new file in the RDS database
* Initiating the new workflow

Configuration
-------------

Popeye's configuration is managed by AppConfig module.  This module
reads the basic configuration from:

* popeye.config

And then overloads the configuration from one of:

* prod.config
* staging.config
* local.config

Depending on what the DEPLOYMENT environment variable is set to, or in
the case that we are running under Apache the mod_wsgi.process_group
string being one of prod, staging, or local

Control Flow
------------

Inbound http requests from Brewtus are handled in popeye.py

popeye.py delegates requests to the /process to the processor_app
defined in processor.py

Within popeye.py add_processor calls instantiate the SQL ORM and the
logger, and assign them to the web.ctx global thread scope.

Then, within processor.py, these variables are extracted and passed to
the Worker constructor.

Worker inherits from Background.

Finally Worker.run() is where the actual work takes place.

worker.py
---------

The Worker class in worker.py drives the execution of the legacy video
processing pipeline.

Worker sets up some shared data structures calls several methods
defined in other modules which perform the video processing.  Throwing
an exception in a module performing video processing means that
processing should be terminated, and the Worker's handle_error method
should be invoked.

Worker has a few key data members:

#### self.popeye_log

A Wsgilogger object which can be passed to other modules in the data
processing pipeline for logging.  This operates much as a typical
Python logging object, however is capable of writing to the webserver
logs.

#### uuid

uuid - the UUID of the media file we are processing

#### files

files - A dictionary data structure, the keys are labels corresponding
to particular types of derived media created during the video
processing (e.g. the main video, posters, thumbnails, alternate
encoding, etc.).  The values are of the format:

       { 
       ifile : ... - The path of the input file for the associated label
       ofile : ... - The path of the output file for the associated label
       key   : ... - The key value for where in S3 this file will be stored
       }

ifile, ofile, and key can have a value of None, if so it means they
are not relevant for the label in question.

#### data

data - a catch call dictionary that holds other information needed by
multiple parts of the pipeline, examples include:

data['info'] - The JSON data structure of the info uploader file

data['metadata'] - The JSON data structure of the metadata uploader file

