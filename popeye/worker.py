# Python librarie
import boto.swf.layer2 as swf
import datetime
import fcntl
import hashlib
import hmac
import json
import logging
import mimetypes
import mixpanel
import ntpath
import os
import platform
import requests
from sqlalchemy import and_
import sys
import threading
import time
import uuid
import web

# Viblio libraries
from appconfig import AppConfig
from background import Background
import helpers
from models import *
sys.path.append("../utils")
import Serialize

# Popeye configuration object.
config = AppConfig( 'popeye' ).config()

# Base class for Worker.
class Worker( Background ):
    '''The class which drives the video processing pipeline.

    This class is a manager, which maintains some common data
    (e.g. filenames and S3 keys), and which initiates various other
    modules to actually perform the video processing.'''

    ######################################################################
    # Initialization
    def __init__( self, SessionFactory, log, data ):
        '''Initialize the worker object.

        First call the base classes __init__ function which sets the
        log and data inputs.
        
        Then create our files data structure.
        '''

        super( Worker, self ).__init__( SessionFactory, log, data )

        self.popeye_log = self.log

        if 'full_filename' in data:
            self.popeye_log.info( "Initializing uuid." )
            self.__initialize_uuid( data['full_filename'] )
            self.popeye_log.info( "Initializing files data structure." )
            self.__initialize_files( data['full_filename'] )
        else:
            self.popeye_log.error( 'No full_filename field found in input data structure.' )
            raise Exception( "Third argument to Worker constructor must have full_filename field" )

        # Also log to a particular logging file.
        try:
            self.popeye_log = None
            file_log = logging.getLogger( 'popeye.' + self.uuid )
            
            file_log.info( "Constructing object for: %s" % self.uuid )

            # Try to remove existing handlers, of which we don't want
            # there to be any.
            current_handlers = file_log.handlers
            for current_handler in current_handlers:
                file_log.warn( "For some reason there are existing handlers, removing handler: %s" % current_handler )
                file_log.removeHandler( current_handler )

            fh = logging.FileHandler( self.files['media_log']['ofile'] )
            fh.setFormatter( logging.Formatter( '%(name)-22s: %(module)-7s: %(lineno)-3s: %(funcName)-12s: %(asctime)s: %(levelname)-5s: %(message)s' ) )
            fh.setLevel( config.loglevel )
            self.popeye_logging_handler = fh
            file_log.addHandler( fh )

            self.popeye_log = file_log

            self.popeye_log.info( 'Logging handlers: %s' % ( self.popeye_log.handlers ) )

            # Mixpanel stuff.
            self.mp_stage = '03'
            try:
                self.mp = mixpanel.Mixpanel( config.mp_token )
                self.mp_web = mixpanel.Mixpanel( config.mp_web_token )
            except Exception as e:
                self.__safe_log( self.popeye_log.warning, "Couldn't instantiate mixpanel instrumentation." )

        except Exception as e:
            print "ERROR: " + str( e )
            raise

    def mp_log( self, event, properties = {} ):
        try:
            if hasattr( self, 'data' ) and 'info' in self.data and 'uid' in self.data['info']:
                properties['user_uuid'] = self.data['info']['uid']  

            if hasattr( self, 'data' ) and 'info' in self.data and 'fileExt' in self.data['info']:
                properties['file_ext'] = self.data['info']['fileExt'].lower()


            properties['media_uuid'] = self.uuid

            mp_deployment = getattr( config, 'mp_deployment', 'unknown' )

            properties['deployment'] = mp_deployment

            event = self.mp_stage + '_' + event
            
            self.mp.track( self.uuid, event, properties )
            if 'user_uuid' in properties:
                self.mp_web.track( properties['user_uuid'], event, properties )

        except Exception as e:
            self.__safe_log( self.popeye_log.warning, "Error sending instrumentation ( %s, %s, %s ) to mixpanel: %s" % ( self.uuid, event, properties, e ) )


    def __del__( self ):
        '''Destructor.'''
        try:
            self.popeye_log.info( "Cleaning up Popeye in destructor." )
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
        except Exception as e:
            print "ERROR: Exception thrown in Popeye destructor: " + str( e ) 
            raise
    

    ######################################################################
    # Main logic
    def run( self ):
        '''Public method: This method is invoked via the following
        call chain:
        
        1) Incoming request is routed to processor.py's processor
        class GET method.

        2) processor.GET creates a Worker object and calls its start
        method in a new thread.

        3) Worker.start is defined in the Background base class in
        background.py, which sets up a database orm connection and
        then calls Worker's run method.'''

        # Convenience variables.
        files = self.files
        log   = self.popeye_log
        orm   = self.orm

        log.info( 'Worker.py, starting to process: ' + self.uuid )

        # Acquire lock.
        self.__acquire_lock()

        # Verify the initial inputs we expect are valid.
        for label in [ 'main', 'info', 'metadata' ]:
            if not self.__valid_file( files[label]['ifile'] ):
                log.error( 'File %s does not exist for label %s' % ( files[label]['ifile'], label ) )
                self.handle_errors()
                if self.popeye_logging_handler:
                    self.popeye_log.removeHandler( self.popeye_logging_handler )
                    self.popeye_logging_handler = None
                raise Exception( 'File %s does not exist for label %s' % ( files[label]['ifile'], label ) )
            else:
                log.info( '%s input file validated.' % label )

        # Load data from .json into self.data['info']
        log.info( 'Initializing info field from JSON file: ' + files['info']['ifile'] )
        self.__initialize_info( files['info']['ifile'] )
        log.info( 'info field is: ' + json.dumps( self.data['info'] ) )
        if 'finalLength' in self.data['info'] and self.data['info']:
            log.debug( 'JSON finalLength is: ' + str( self.data['info']['finalLength'] ) )

        # Check if we've already seen this file for this user.
        unique_hash = None
        try:
            log.info( 'Computing MD5SUM for input file: %s' % ( files['main']['ifile'] ) )
            
            f = open( files['main']['ifile'], 'rb' )
            md5 = hashlib.md5()
            while True:
                file_data = f.read( 1048576 )
                if not file_data:
                    break
                md5.update( file_data )
            unique_hash = md5.hexdigest()
            f.close()

            log.debug( 'Getting the current user from the database for uid: %s' % ( self.data['info']['uid'] ) )
            user = orm.query( Users ).filter_by( uuid = self.data['info']['uid'] ).one()

            log.debug( 'Checking uniqueness of file with hash %s for uid %s' % ( unique_hash, self.data['info']['uid'] ) )
            db_files = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.unique_hash == unique_hash ) ).all()

            if len( db_files ) == 0:
                log.info( 'File with hash %s for user uuid %s is unique, proceeding.' % ( unique_hash, self.data['info']['uid'] ) )
            else:
                log.info( 'File with hash %s for user uuid %s is not unique, terminating.' % ( unique_hash, self.data['info']['uid'] ) )
                self.handle_errors()
                self.__release_lock()
                if self.popeye_logging_handler:
                    self.popeye_log.removeHandler( self.popeye_logging_handler )
                    self.popeye_logging_handler = None
                return

        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to determine uniqueness of uploaded file: %s' % ( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise


        # Load data from _metadata.json into self.data['metadata']
        log.info( 'Initializing metadata field from JSON file: ' + files['metadata']['ifile'] )
        self.__initialize_metadata( files['metadata']['ifile'] )
        log.info( 'metadata field is: ' + json.dumps( self.data['metadata'] ) )

        #self.mp_log( '010_input_validated' )

        ######################################################################
        # Upload files to S3.
        #

        try:
            # Iterate over all the labels in files and upload anything
            # with an ofile and a key.
            for label in files:
                if files[label]['key'] and files[label]['ofile'] and self.__valid_file( files[label]['ofile'] ):
                    log.info( 'Starting upload for %s to %s' % ( files[label]['ofile'], files[label]['key'] ) )
                    helpers.upload_file( files[label], log, self.data )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to upload to S3: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        self.mp_log( '070_store_s3_completed' )

        #######################################################################
        # DATABASE
        #

        try:
            # Media row
            log.info( 'Generating row for media file' )
            client_filename = os.path.basename( files['main']['ofile'] )
            if self.data['metadata'] and self.data['metadata']['file'] and self.data['metadata']['file']['Path']:
                client_filename = self.data['metadata']['file']['Path']

            log.info( 'Getting the current user from the database for uid: ' + self.data['info']['uid'] )
            user = orm.query( Users ).filter_by( uuid = self.data['info']['uid'] ).one()

            media_title = None
            if 'file' in self.data['metadata']:
                if 'Path' in self.data['metadata']['file']:
                    if len( self.data['metadata']['file']['Path'] ):
                        media_title = os.path.splitext( ntpath.basename( self.data['metadata']['file']['Path'] ) )[0]

            media = Media( uuid           = self.uuid,
                           media_type     = 'original',
                           filename       = client_filename,
                           title          = media_title,
                           view_count     = 0,
                           status         = 'pending',
                           unique_hash    = unique_hash )

            mwfs = MediaWorkflowStages( workflow_stage = 'PopeyeComplete' )
            media.media_workflow_stages.append( mwfs )

            # Associate media with user.
            user.media.append( media )
            
            original_uuid = str( uuid.uuid4() )

            video_asset = MediaAssets( 
                uuid         = original_uuid,
                asset_type   = 'original',
                metadata_uri = files['metadata']['key'],
                bytes        = os.path.getsize( files['main']['ifile'] ),
                uri          = files['main']['key'],
                location     = 'us',
                view_count   = 0 )
            media.assets.append( video_asset )

        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to add mediafile to database: %s' % str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to commit the database: %s' % str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        self.mp_log( '080_store_db_completed' )

        ################################
        # NEW PIPELINE CALLOUT
        ################################
        try:
            log.info( 'Making call to Video Processing Workflow external to Popeye, task list: %s' % ( 'VPDecider' + config.VPWSuffix + config.UniqueTaskList ) )

            execution = swf.WorkflowType( 
                name = 'VideoProcessing' + config.VPWSuffix, 
                domain = 'Viblio', version = '1.0.7' 
                ).start( 
                task_list = 'VPDecider' + config.VPWSuffix + config.UniqueTaskList, 
                input = json.dumps( { 
                            'media_uuid' : self.uuid, 
                            'user_uuid'  : self.data['info']['uid'],
                            'original_uuid' : original_uuid,
                            'input_file' : {
                                's3_bucket'  : config.bucket_name,
                                's3_key' : files['main']['key']
                                },
                            'metadata_uri' : files['metadata']['key'],
                            'outputs' : [ { 
                                    'output_file' : {
                                        's3_bucket' : config.bucket_name,
                                        's3_key' : "%s_output.mp4" % ( files['main']['key'] ),
                                        },
                                    'format' : 'mp4',
                                    'max_video_bitrate' : 1500,
                                    'audio_bitrate' : 160,
                                    'asset_type' : 'main',
                                    'thumbnails' : [ {
                                            'times' : [ 0.5 ],
                                            'type'  : 'static',
                                            'size'  : "320x240",
                                            'label' : 'poster',
                                            'format' : 'png',
                                            'output_file' : {
                                                's3_bucket' : config.bucket_name,
                                                's3_key' : "%s_poster.png" % ( files['main']['key'] )
                                                }
                                            }, 
                                                     {
                                            'times' : [ 0.5 ],
                                            'size': "128x128",
                                            'type'  : 'static',
                                            'label' : 'thumbnail',
                                            'format' : 'png',
                                            'output_file' : {
                                                's3_bucket' : config.bucket_name,
                                                's3_key' : "%s_thumbnail.png" % ( files['main']['key'] )
                                                }
                                            },
                                                     {
                                            'times' : [ 0.5 ],
                                            'type'  : 'animated',
                                            'size'  : "320x240",
                                            'label' : 'poster_animated',
                                            'format' : 'gif',
                                            'output_file' : {
                                                's3_bucket' : config.bucket_name,
                                                's3_key' : "%s_poster_animated.gif" % ( files['main']['key'] )
                                                }
                                            },
                                                     {
                                            'times' : [ 0.5 ],
                                            'size': "128x128",
                                            'type'  : 'animated',
                                            'label' : 'thumbnail_animated',
                                            'format' : 'gif',
                                            'output_file' : {
                                                's3_bucket' : config.bucket_name,
                                                's3_key' : "%s_thumbnail_animated.gif" % ( files['main']['key'] )
                                                }
                                            } ]
                                    }
                                          ]
                            } ),
                workflow_id=self.uuid 
                )
                
            log.info( 'External Video Processing Workflow %s initiated' % execution.workflowId )

            self.mp_log( '090_new_pipeline_callout' )

        except Exception as e:
            log.warning( "Failed to launch External Video Processing Workflow, error was: %s" % e )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        ######################################################################
        # Cleanup files on success.
        ######################################################################
        try:
            log.info( 'File successfully processed, removing temp files ...' )
            for label in files:
                # Iterate over the files data structure and remove
                # anything with an ifile or ofile.
                for file_type in [ 'ifile', 'ofile' ]:
                    if files[label][file_type] and self.__valid_file( files[label][file_type] ):
                        os.remove( files[label][file_type] )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Some trouble removing temp files: %s' % str( e ) )
            self.handle_errors()

        self.__release_lock()

        log.info( 'DONE WITH %s' % self.uuid )

        #self.mp_log( '140_popeye_completed' )

        if self.popeye_logging_handler:
            self.popeye_log.removeHandler( self.popeye_logging_handler )
            self.popeye_logging_handler = None
        return

    ######################################################################
    # Error handling
    def handle_errors( self ):
        '''Copy temporary files to error directory.'''
        try:
            files = self.files
            log = self.popeye_log
            self.__safe_log( log.info, 'Error occurred, relocating temp files to error directory...' )

            for label in files:
                for file_type in [ 'ifile', 'ofile' ]:
                    if files[label][file_type] and self.__valid_file( files[label][file_type] ):
                        try: 
                            full_name = files[label][file_type]
                            base_path = os.path.split( full_name )[0]
                            file_name = os.path.split( full_name )[1]
                            os.rename( full_name, base_path + '/errors/' + file_name )
                        except Exception as e_inner:
                            self.__safe_log( self.popeye_log.exception, 'Failed to rename file: ' + full_name )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Some trouble relocating temp files temp files: %s' % str( e ) )

    def __acquire_lock( self ):
        try:
            # Create the file if it doesn't exist, open it if it does.
            log = self.popeye_log
            self.lockfile_name = self.data['full_filename'] + '.lock'
            log.info( 'Attempting to create lock file: ' + self.lockfile_name )
            self.lockfile = open( self.lockfile_name, 'a' )
            log.info( 'Attempting to acquire lock: ' + self.lockfile_name )
            self.lock_data = fcntl.flock( self.lockfile, fcntl.LOCK_EX|fcntl.LOCK_NB )
            self.lock_acquired = True
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to acquire lock, error: ' + str( e ) )
            raise

    def __release_lock( self ):
        try:
            # Create the file if it doesn't exist, open it if it does.
            log = self.popeye_log
            if hasattr( self, 'lock_acquired' ):
                log.info( 'Attempting to release lock file: ' + self.lockfile_name )
                fcntl.flock( self.lockfile, fcntl.LOCK_UN )
                self.lock_acquired = False
                log.info( 'Attempting to remove lock file: ' + self.lockfile_name )
                os.remove( self.lockfile_name )
            else:
                log.warn( '__release_lock called but no lock held: ' + self.lockfile_name )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to release lock, error: ' + str( e ) )
            raise
        finally:
            try:
                os.remove( self.lockfile_name )
            except:
                pass
            if hasattr( self, 'lock_acquired' ):
                self.lock_acquired = False

    ######################################################################
    # Utility function to add things to our files data structure
    def add_file( self, label, ifile=None, ofile=None, key=None ):
        '''Public method: Attempt to add files[label] = { ifile,
        ofile, key } to the files data structure.
        '''
        try:
            if label in self.files:
                self.popeye_log.info( 'Overwriting existing file label: %s with new values.' % label )
                self.popeye_log.debug( 'Old %s label ifile is: %s' % 
                               ( label, self.files[label].get( 'ifile', 'No ifile key' ) ) )
                self.popeye_log.debug( 'Old %s label ofile is: %s' % 
                               ( label, self.files[label].get( 'ofile', 'No ofile key' ) ) )
                self.popeye_log.debug( 'Old %s label key is: %s' % 
                               ( label, self.files[label].get( 'key', "No key called 'key'" ) ) )
            else:
                self.popeye_log.info( 'Adding new file label: %s with new values.' % label )

            self.files[label] = { 'ifile' : ifile, 'ofile' : ofile, 'key' : key }

            return

        except Exception as e:
            self.__safe_log( self.popeye_log.exception, "Exception thrown while adding file: %s" % str( e ) )
            raise

    ######################################################################
    # Utility function to check if a given file exists and is readable
    def __valid_file( self, input_filename ):
        '''Private method: Return true if input_filename exists and is
        readable, and false otherwise.'''

        if os.path.isfile( input_filename ):
            if os.access( input_filename, os.R_OK ):
                self.popeye_log.debug( 'File %s is %s bytes.' % ( input_filename, str( os.path.getsize( input_filename ) ) ) )
                return True
            else:
                self.popeye_log.warn( 'File %s exists but is not readable.' % input_filename )
                return False
        else:
            self.popeye_log.debug( 'File %s does not exist.' % input_filename )
            return False

    ######################################################################
    # Utility function to log and not throw exceptions if there is an
    # error while logging.
    def __safe_log( self, logger, message ):
        '''Private method: Used for when we are trying to log in an
        exception block - in this case we want to be careful to not
        blow out our error handling code due to a problem with
        logging.'''
        try:
            logger( str( message ) )
        except Exception as e:
            print "Exception thrown while logging error:" % str( e )

        return

    ######################################################################
    # Various internal initialization functions below.
    def __initialize_info( self, ifile ):
        '''Load the contents of the info input file into the info field from
        JSON'''
        try:
            f = open( ifile )
            self.data['info'] = json.load( f )
        except Exception as e:
            self.popeye_log.exception( 'Failed to open and parse as JSON: %s error was: %s' % ( ifile, str( e ) ) )
            self.handle_errors()
            raise

    def __initialize_uuid( self, input_filename ):
        '''Private method: We expect an input filename that is the
        UUID of the media file that has been uploaded.  We store this
        value in self.uuid.
        '''
        self.__valid_file( input_filename )
        self.uuid = os.path.splitext( os.path.basename( input_filename ) )[0]
        self.popeye_log.info( "Set uuid to %s" % self.uuid )

    def __initialize_metadata( self, ifile ):
        '''Load the contents of the metadata input file into the
        metadata field from JSON'''
        try:
            f = open( ifile )
            self.data['metadata'] = json.load( f )
        except Exception as e:
            self.popeye_log.exception( 'Failed to open and parse %s as JSON error was %s' % ( ifile, str( e ) ) )
            self.handle_errors()
            raise

    def __initialize_files( self, input_filename ):
        '''Private method: Populate the files data structure for the
        worker class.  Files is a dictionary where:

        * Each key corresponds to a type of file in the video
          processing pipeline (e.g. original, mp4, thumbnail, etc.)

        * Each value is itself a dictionary, with the following keys
          as appropriate:
          + ifile - the full file system path of the input to this
            stage of the pipeline

          + ofile - the full file system path of the output of this
            stage of the pipeline

          + key - the key that the output resource will be associated
            with in persistent storage (currently S3)
          '''
        try:
            self.files = {}

            abs_basename = os.path.splitext( input_filename )[0]

            # The 'main' media file, an mp4.
            self.add_file( 
                label = 'main',
                ifile = input_filename, 
                ofile = input_filename, 
                key   = self.uuid + '/' + self.uuid )
            
            # The 'metadata' media file, json.
            self.add_file( 
                label = 'metadata',
                ifile = abs_basename+'_metadata.json', 
                ofile = abs_basename+'_metadata.json', 
                key   = self.uuid + '/' + self.uuid + '_metadata.json' )

            # The 'info' media file, json.
            self.add_file( 
                label = 'info',
                ifile = abs_basename+'.json', 
                ofile = abs_basename+'.json', 
                key   = self.uuid + '/' + self.uuid + '.json' )

            # Self log file.
            self.add_file( 
                label = 'media_log',
                ifile = None, 
                ofile = abs_basename+'.log', 
                key   = None )

        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Error while initializing files: ' + str( e ) )
            self.handle_errors()
            return 

