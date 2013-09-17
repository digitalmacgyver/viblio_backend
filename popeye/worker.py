import web
import json
import uuid
import hmac
from models import *
import os

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

import logging

import sys
import requests

import helpers
import video_processing
import mimetypes

# Base class for Worker.
from background import Background

class Worker(Background):
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

        if 'full_filename' in data:
            self.log.info( "Initializing uuid." )
            self.__initialize_uuid( data['full_filename'] )
            self.log.info( "Initializing files data structure." )
            self.__initialize_files( data['full_filename'] )
        else:
            self.log.error( 'No full_filename field found in input data structure.' )
            raise Exception( "Third argument to Worker constructor must have full_filename field" )

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
        log   = self.log
        orm   = self.orm

        # Also log to a particular logging file.
        logging.basicConfig( filename = files['media_log']['ofile'], level = config.loglevel )

        log.info( 'Worker.py, starting to process: ' + self.uuid )

        # Verify the initial inputs we expect are valid.
        for label in [ 'main', 'info', 'metadata' ]:
            if not self.__valid_file( files[label]['ifile'] ):
                log.error( 'File %s does not exist for label %s' % ( files[label]['ifile'], label ) )
                self.handle_errors()
                return
            else:
                log.info( '%s input file validated.' % label )

        # Load data from .json into self.data['info']
        log.info( 'Initializing info field from JSON file: ' + files['info']['ifile'] )
        self.__initialize_info( files['info']['ifile'] )
        log.info( 'info field is: ' + json.dumps( self.data['info'] ) )

        # Load data from _metadata.json into self.data['metadata']
        log.info( 'Initializing metadata field from JSON file: ' + files['metadata']['ifile'] )
        self.__initialize_metadata( files['metadata']['ifile'] )
        log.info( 'metadata field is: ' + json.dumps( self.data['metadata'] ) )

        # Give the input file an extension.
        log.info( 'Renaming input file %s with lower cased file extension based on uploader information' % files['main']['ifile'] )
        try:
            new_filename = helpers.rename_upload_with_extension( files['main'], log, self.data )
            log.info( 'Renamed input file is: ' + new_filename )
            files['main']['ifile'] = new_filename
        except Exception as e:
            self.__safe_log( log.error, 'Could not rename input file, error was: ' + str( e ) )
            self.handle_errors()
            raise

        # Generate _exif.json and load it into self.data['exif']
        log.info( 'Getting exif data from file %s and storing it to %s' % ( files['exif']['ifile'], files['exif']['ofile'] ) )
        try:
            self.data['exif'] = helpers.get_exif( files['exif'], log, self.data )
            log.info( 'EXIF data extracted: ' + str( self.data['exif'] ) )
        except Exception as e:
            self.__safe_log( log.error, 'Error during exif extraction: ' + str( e ) )
            self.handle_errors()
            raise

        # Extract the mimetype and store it in self.data['mimetype']
        log.info( 'Getting mime type of input video.' )
        try:
            self.data['mimetype'] = mimetypes.guess_type( files['main']['ifile'] )[0]
            log.info( 'Mime type was ' + self.data['mimetype'] )
        except Exception as e:
            self.__safe_log( log.error, 'Failed to get mime type, error was: ' + str( e ) )
            self.handle_errors()
            raise

        try: 
            # Transcode into mp4 and rotate as needed.
            log.info( 'Transcode %s to %s' % ( files['main']['ifile'], files['main']['ofile'] ) )
            video_processing.transcode_main( files['main'], log, self.data )

            # Move the atom to the front of the file.
            log.info( 'Move atom for: ' + files['main']['ofile'] )
            video_processing.move_atom( files['main'], log, self.data )
            
            # Create an AVI for intellivision.
            log.info( 'Transcode %s to %s' % ( files['intellivision']['ifile'], files['intellivision']['ofile'] ) )
            video_processing.transcode_avi( files['intellivision'], log, self.data )

            # Create a poster.
            log.info( 'Generate poster from %s to %s' % ( files['poster']['ifile'], files['poster']['ofile'] ) )
            video_processing.generate_poster( files['poster'], log, self.data )
            
            # Create a thumbnail.
            log.info( 'Generate thumbnail from %s to %s' % ( files['thumbnail']['ifile'], files['thumbnail']['ifile'] ) )
            video_processing.generate_thumbnail( files['thumbnail'], log, self.data )

            # Generate a single face.
            log.info( 'Generate face from %s to %s' % ( files['face']['ifile'], files['face']['ofile'] ) )
            # If skip = True we simply skip face generation.
            video_processing.generate_face( files['face'], log, self.data, skip=False )

        except Exception as e:
            self.__safe_log( log.error, str( e ) )
            self.handle_errors()
            raise

        ######################################################################
        # Upload files to S3.
        #

        try:
            # Iterate over all the labels in files and upload anything with an ofile and a key.
            for label in files:
                if files[label]['key'] and files[label]['ofile'] and self.__valid_file( files[label]['ofile'] ):
                    log.info( 'Starting upload for %s to %s' % ( files[label]['ofile'], files[label]['key'] ) )
                    helpers.upload_file( files[label], log, self.data )
        except Exception as e:
            self.__safe_log( log.error, 'Failed to upload to S3: ' + str( e ) )
            self.handle_errors()
            raise

        #######################################################################
        # DATABASE
        #

        try:
            # Media row
            log.info( 'Generating row for media file' )
            client_filename = os.path.basename( files['main']['ifile'] )
            if self.data['metadata'] and self.data['metadata']['file'] and self.data['metadata']['file']['Path']:
                client_filename = self.data['metadata']['file']['Path']

            media = Media( uuid           = self.uuid,
                           media_type     = 'original',
                           recording_date = self.data['exif']['create_date'],
                           lat            = self.data['exif']['lat'],
                           lng            = self.data['exif']['lng'],
                           filename       = client_filename )

            # Main media_asset
            log.info( 'Generating row for main media_asset' )
            asset = MediaAssets( uuid        = str(uuid.uuid4()),
                                asset_type   = 'main',
                                mimetype     = self.data['mimetype'],
                                metadata_uri = files['metadata']['key'],
                                bytes        = os.path.getsize( files['main']['ofile'] ),
                                uri          = files['main']['key'],
                                location     = 'us' )
            media.assets.append( asset )

            # Intellivision media_asset
            log.info( 'Generating row for intellivision media_asset' )
            avi_asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                     asset_type = 'intellivision',
                                     mimetype   = 'video/avi',
                                     bytes      = os.path.getsize( files['intellivision']['ofile'] ),
                                     uri        = files['intellivision']['key'],
                                     location   = 'us' )
            media.assets.append( avi_asset )

            # Thumbnail media_asset
            log.info( 'Generating row for thumbnail media_asset' )
            asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                 asset_type = 'thumbnail',
                                 mimetype   = 'image/jpg',
                                 bytes      = os.path.getsize( files['thumbnail']['ofile'] ),
                                 width      = 128, 
                                 height     = 128,
                                 uri        = files['thumbnail']['key'],
                                 location   = 'us' )
            media.assets.append( asset )

            # Poster media_asset
            log.info( 'Generating row for poster media_asset' )
            poster_asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                        asset_type = 'poster',
                                        mimetype   = 'image/jpg',
                                        bytes      = os.path.getsize( files['poster']['ofile'] ),
                                        width      = 320,
                                        height     = 180,
                                        uri        = files['poster']['key'],
                                        location   = 'us' )
            media.assets.append( poster_asset )

            if self.data['found_faces']:
                log.info( 'Generating row for face media_asset' )

                # Face media_asset.
                face_asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                          asset_type = 'face',
                                          mimetype   = 'image/jpg',
                                          bytes      = os.path.getsize( files['face']['ofile'] ),
                                          width      = 128, 
                                          height     = 128,
                                          uri        = files['face']['key'],
                                          location   = 'us' )
                media.assets.append( face_asset )

                log.info( 'Generating for for face media_asset_feature' )
                face_feature = MediaAssetFeatures( feature_type = 'face',
                                                   )
                # Face media_asset_feature.
                face_asset.media_asset_features.append( face_feature )

            log.info( 'Getting the current user from the database for uid: ' + self.data['info']['uid'] )
            user = orm.query( Users ).filter_by( uuid = self.data['info']['uid'] ).one()

            # Associate media with user.
            user.media.append( media )

        except Exception as e:
            self.__safe_log( log.error, 'Failed to add mediafile to database!: %s' % str( e ) )
            self.handle_errors()
            raise

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.__safe_log( log.error, 'Failed to commit the database: %s' % str( e ) )
            self.handle_errors()
            raise

        #######################################################################
        # Send notification to CAT server.
        #######################################################################
        try:
            log.info( 'Notifying Cat server at %s' %  config.viblio_server_url )
            site_token = hmac.new( config.site_secret, self.data['info']['uid'] ).hexdigest()
            res = requests.get( config.viblio_server_url, params={ 'uid': self.data['info']['uid'], 'mid': self.uuid, 'site-token': site_token } )
            body = ''
            if hasattr( res, 'text' ):
                body = res.text
            elif hasattr( res, 'content' ):
                body = str( res.content )
            else:
                log.error( 'Cannot find body in response!' )
            jdata = json.loads( body )
            if 'error' in jdata:
                raise Exception( jdata['message'] )
        except Exception as e:
            self.__safe_log( log.error, 'Failed to notify Cat: %s' % str( e ) )
            self.handle_errors()
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
            self.__safe_log( log.error, 'Some trouble removing temp files: %s' % str( e ) )
            self.handle_errors()

        log.info( 'DONE WITH %s' % self.uuid )

        return

    ######################################################################
    # Error handling
    def handle_errors( self ):
        '''Copy temporary files to error directory.'''
        try:
            files = self.files
            log = self.log
            log.info( 'Error occurred, relocating temp files to error directory...' )

            for label in files:
                for file_type in [ 'ifile', 'ofile' ]:
                    if files[label][file_type] and self.__valid_file( files[label][file_type] ):
                        try: 
                            full_name = files[label][file_type]
                            base_path = os.path.split( full_name )[0]
                            file_name = os.path.split( full_name )[1]
                            os.rename( full_name, base_path + '/errors/' + file_name )
                        except Exception as e_inner:
                            self.__safe_log( log.error, 'Failed to rename file: ' + full_name )
        except Exception as e:
            self.__safe_log( log.error, 'Some trouble relocating temp files temp files: %s' % str( e ) )

    ######################################################################
    # Utility function to add things to our files data structure
    def add_file( self, label, ifile=None, ofile=None, key=None ):
        '''Public method: Attempt to add files[label] = { ifile,
        ofile, key } to the files data structure.
        '''
        try:
            if label in self.files:
                self.log.info( 'Overwriting existing file label: %s with new values.' % label )
                self.log.debug( 'Old %s label ifile is: %s' % 
                               ( label, files[label].get( 'ifile', 'No ifile key' ) ) )
                self.log.debug( 'Old %s label ofile is: %s' % 
                               ( label, files[label].get( 'ofile', 'No ofile key' ) ) )
                self.log.debug( 'Old %s label key is: %s' % 
                               ( label, files[label].get( 'key', "No key called 'key'" ) ) )
            else:
                self.log.info( 'Adding new file label: %s with new values.' % label )

            self.files[label] = { 'ifile' : ifile, 'ofile' : ofile, 'key' : key }

            self.log.debug( 'New %s label ifile is: %s' % ( label, ifile ) )
            self.log.debug( 'New %s label ofile is: %s' % ( label, ofile ) )
            self.log.debug( 'New %s label key is: %s' % ( label, key ) )

            return

        except Exception as e:
            self.__safe_log( self.log.error, "Exception thrown while adding file: %s" % str( e ) )
            raise

    ######################################################################
    # Utility function to check if a given file exists and is readable
    def __valid_file( self, input_filename ):
        '''Private method: Return true if input_filename exists and is
        readable, and false otherwise.'''
        self.log.debug( 'Checking whether file %s exists and is readable.' % input_filename )
        if os.path.isfile( input_filename ):
            self.log.debug( 'File %s exists.' % input_filename )

            if os.access( input_filename, os.R_OK ):
                self.log.debug( 'File %s is readable.' % input_filename )
                return True
            else:
                self.log.warn( 'File %s exists but is not readable.' % input_filename )
                return False
        else:
            self.log.debug( 'File %s does not exist.' % input_filename )
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
            log.error( 'Failed to open and parse as JSON: %s error was: %s' % ( ifile, str( e ) ) )
            self.handle_errors()
            raise

    def __initialize_uuid( self, input_filename ):
        '''Private method: We expect an input filename that is the
        UUID of the media file that has been uploaded.  We store this
        value in self.uuid.
        '''
        self.__valid_file( input_filename )
        self.uuid = os.path.splitext( os.path.basename( input_filename ) )[0]
        self.log.info( "Set uuid to %s" % self.uuid )

    def __initialize_metadata( self, ifile ):
        '''Load the contents of the metadata input file into the
        metadata field from JSON'''
        try:
            f = open( ifile )
            self.data['metadata'] = json.load( f )
        except Exception as e:
            log.error( 'Failed to open and parse %s as JSON error was %s' % ( ifile, str( e ) ) )
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
                ofile = abs_basename + '.mp4', 
                key   = self.uuid + '/' + self.uuid + '.mp4' )
            
            # The 'thumbnail' media file, a jpg.
            self.add_file( 
                label = 'thumbnail',
                ifile = abs_basename+'.mp4', 
                ofile = abs_basename+'_thumbnail.jpg', 
                key   = self.uuid + '/' + self.uuid + '_thumbnail.jpg' )
            
            # The 'poster' media file, a jpg.
            self.add_file( 
                label = 'poster',
                ifile = abs_basename+'.mp4', 
                ofile = abs_basename+'_poster.jpg', 
                key   = self.uuid + '/' + self.uuid + '_poster.jpg' )
            
            # The 'face' media file, json.
            self.add_file( 
                label = 'face',
                ifile = abs_basename+'.mp4', 
                ofile = abs_basename+'_face0.jpg', 
                key   = self.uuid + '/' + self.uuid + '_face0.jpg' )
            
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

            # The 'exif' media file, json
            self.add_file( 
                label = 'exif',
                ifile = input_filename+'.mp4', 
                ofile = abs_basename+'_exif.json', 
                key   = self.uuid + '/' + self.uuid + '_exif.json' )

            # The 'intellivision' media file, by convention an AVI.
            self.add_file( 
                label = 'intellivision',
                ifile = abs_basename+'.mp4', 
                ofile = abs_basename+'.avi', 
                key   = self.uuid + '/' + self.uuid + '.avi' )

            # Self log file.
            self.add_file( 
                label = 'media_log',
                ifile = None, 
                ofile = abs_basename+'.log', 
                key   = None )

        except Exception as e:
            self.__safe_log( self.log.error, 'Error while initializing files: ' + str( e ) )
            self.handle_errors()
            return 

