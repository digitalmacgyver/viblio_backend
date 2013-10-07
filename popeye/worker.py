# Python libraries
import datetime
import fcntl
import hmac
import json
import logging
import mimetypes
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
import video_processing


# Popeye configuration object.
config = AppConfig( 'popeye' ).config()

# Base class for Worker.
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
            file_log = logging.getLogger( 'popeye.' + str( threading.current_thread().ident ) )
            fh = logging.FileHandler( self.files['media_log']['ofile'] )
            fh.setFormatter( logging.Formatter( '%(name)s: %(asctime)s %(levelname)-4s %(message)s' ) )
            fh.setLevel( config.loglevel )
            self.popeye_logging_handler = fh
            file_log.addHandler( fh )

            self.popeye_log = file_log
        except Exception as e:
            print "ERROR: " + str( e )
            raise

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
                return
            else:
                log.info( '%s input file validated.' % label )

        # Load data from .json into self.data['info']
        log.info( 'Initializing info field from JSON file: ' + files['info']['ifile'] )
        self.__initialize_info( files['info']['ifile'] )
        log.info( 'info field is: ' + json.dumps( self.data['info'] ) )
        if 'finalLength' in self.data['info'] and self.data['info']:
            log.debug( 'JSON finalLength is: ' + str( self.data['info']['finalLength'] ) )

        # Load data from _metadata.json into self.data['metadata']
        log.info( 'Initializing metadata field from JSON file: ' + files['metadata']['ifile'] )
        self.__initialize_metadata( files['metadata']['ifile'] )
        log.info( 'metadata field is: ' + json.dumps( self.data['metadata'] ) )

        # Generate _exif.json and load it into self.data['exif']
        log.info( 'Getting exif data from file %s and storing it to %s' % ( files['exif']['ifile'], files['exif']['ofile'] ) )
        try:
            self.data['exif'] = helpers.get_exif( files['exif'], log, self.data )
            log.info( 'EXIF data extracted: ' + str( self.data['exif'] ) )
        except Exception as e:
            self.__safe_log( log.error, 'Error during exif extraction: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            raise

        # Give the input file an extension.
        log.info( 'Renaming input file %s with lower cased file extension based on uploader information' % files['main']['ifile'] )
        try:
            new_filename = helpers.rename_upload_with_extension( files['main'], log, self.data )
            log.info( 'Renamed input file is: ' + new_filename )
            files['main']['ifile'] = new_filename
        except Exception as e:
            self.__safe_log( log.error, 'Could not rename input file, error was: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            raise

        # Extract the mimetype and store it in self.data['mimetype']
        log.info( 'Getting mime type of input video.' )
        try:
            self.data['mimetype'] = str( mimetypes.guess_type( files['main']['ifile'] )[0] )
            log.info( 'Mime type was ' + self.data['mimetype'] )
        except Exception as e:
            self.__safe_log( log.error, 'Failed to get mime type, error was: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            raise

        try: 
            # Transcode into mp4 and rotate as needed.
            log.info( 'Transcode %s to %s' % ( files['main']['ifile'], files['main']['ofile'] ) )
            log.info( 'Before transcoding file %s is %s bytes.' % ( files['main']['ifile'], str( os.path.getsize( files['main']['ifile'] ) ) ) )
            video_processing.transcode_main( files['main'], log, self.data )
            log.info( 'Transcoded mime type is ' + self.data['mimetype'] )
            log.info( 'After transcoding file %s is %s bytes.' % ( files['main']['ofile'], str( os.path.getsize( files['main']['ofile'] ) ) ) )

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
            log.info( 'Generate thumbnail from %s to %s' % ( files['thumbnail']['ifile'], files['thumbnail']['ofile'] ) )
            video_processing.generate_thumbnail( files['thumbnail'], log, self.data )

            # Generate a single face.
            log.info( 'Generate face from %s to %s' % ( files['face']['ifile'], files['face']['ofile'] ) )
            # If skip = True we simply skip face generation.
            video_processing.generate_face( files['face'], log, self.data, skip=True )

        except Exception as e:
            self.__safe_log( log.error, str( e ) )
            self.handle_errors()
            self.__release_lock()
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
            self.__release_lock()
            raise

        #######################################################################
        # DATABASE
        #

        try:
            # Media row
            log.info( 'Generating row for media file' )
            client_filename = os.path.basename( files['main']['ofile'] )
            if self.data['metadata'] and self.data['metadata']['file'] and self.data['metadata']['file']['Path']:
                client_filename = self.data['metadata']['file']['Path']

            recording_date = datetime.datetime.now()
            if self.data['exif']['create_date'] and self.data['exif']['create_date'] != '' and self.data['exif']['create_date'] != '0000:00:00 00:00:00':
                recording_date = self.data['exif']['create_date']
            log.debug( 'Setting recording date to ' + str( recording_date ) )
            log.debug( 'Exif data for create was ' + self.data['exif']['create_date'] )

            log.info( 'Getting the current user from the database for uid: ' + self.data['info']['uid'] )
            user = orm.query( Users ).filter_by( uuid = self.data['info']['uid'] ).one()

            media = Media( uuid           = self.uuid,
                           media_type     = 'original',
                           recording_date = recording_date,
                           lat            = self.data['exif']['lat'],
                           lng            = self.data['exif']['lng'],
                           filename       = client_filename,
                           view_count     = 0 )

            # Associate media with user.
            user.media.append( media )
            
            # Main media_asset
            log.info( 'Generating row for main media_asset' )
            asset = MediaAssets( uuid        = str(uuid.uuid4()),
                                asset_type   = 'main',
                                mimetype     = self.data['mimetype'],
                                metadata_uri = files['metadata']['key'],
                                bytes        = os.path.getsize( files['main']['ofile'] ),
                                uri          = files['main']['key'],
                                location     = 'us',
                                view_count   = 0 )
            media.assets.append( asset )

            # Intellivision media_asset
            log.info( 'Generating row for intellivision media_asset' )
            avi_asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                     asset_type = 'intellivision',
                                     mimetype   = 'video/avi',
                                     bytes      = os.path.getsize( files['intellivision']['ofile'] ),
                                     uri        = files['intellivision']['key'],
                                     location   = 'us',
                                     view_count = 0)
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
                                 location   = 'us',
                                 view_count = 0 )
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
                                        location   = 'us',
                                        view_count = 0 )
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
                                          location   = 'us',
                                          view_count = 0 )
                media.assets.append( face_asset )

                log.info( 'Generating for for face media_asset_feature' )
                face_feature = MediaAssetFeatures( feature_type = 'face',
                                                   )
                # Face media_asset_feature.
                face_asset.media_asset_features.append( face_feature )

        except Exception as e:
            self.__safe_log( log.error, 'Failed to add mediafile to database: %s' % str( e ) )
            self.handle_errors()
            self.__release_lock()
            raise

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.__safe_log( log.error, 'Failed to commit the database: %s' % str( e ) )
            self.handle_errors()
            self.__release_lock()
            raise

        # Serialize any operations by user and detect faces.
        try:
            # user = orm.query( Users ).filter_by( uuid = self.data['info']['uid'] ).one()
            # DEBUG - Pending dependent work elsewhere.
            # Handle intellivision faces, which relate to the media row.

            self.faces_lock = Serialize.Serialize( app         = 'popeye',
                                                   object_name = self.data['info']['uid'], 
                                                   owner_id    = self.uuid,
                                                   app_config  = config,
                                                   heartbeat   = 30 )
            self.faces_lock.acquire()

            # DEBUG - easily turn this on and off for testing
            # purposes.
            if True:
                # self.data['track_json'] = helpers.get_iv_tracks( files['intellivision'], log, self.data )

                log.info( 'Making call to get faces' )
                self.data['track_json'] = video_processing.get_faces( files['intellivision'], log, self.data )
                log.info( 'Get faces returned.' )

                if self.data['track_json'] == None:
                    log.info( 'Video processing did not return any tracks.' )
                else:
                    log.info( 'Storing contacts and faces from Intellivision.' )
                    log.debug( "JSON is: " + self.data['track_json'] )
                    self.store_faces( media, user )

            self.faces_lock.release()
        except Exception as e:
            try:
                if hasattr( self, 'faces_lock' ) and self.faces_lock:
                    self.faces_lock.release()
                log.error( "Failed to process faces, errors: " + str( e ) )
            except:
                pass
            self.handle_errors()
            self.__release_lock()
            raise

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.__safe_log( log.error, 'Failed to commit the database: %s' % str( e ) )
            self.handle_errors()
            self.__release_lock()
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
            self.__release_lock()
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

        self.__release_lock()

        log.info( 'DONE WITH %s' % self.uuid )

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
                            self.__safe_log( log.error, 'Failed to rename file: ' + full_name )
        except Exception as e:
            self.__safe_log( log.error, 'Some trouble relocating temp files temp files: %s' % str( e ) )

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
            self.__safe_log( log.error, 'Failed to acquire lock, error: ' + str( e ) )
            raise

    def __release_lock( self ):
        try:
            # Create the file if it doesn't exist, open it if it does.
            log = self.popeye_log
            if getattr( self, 'lock_acquired' ):
                log.info( 'Attempting to release lock file: ' + self.lockfile_name )
                fcntl.flock( self.lockfile, fcntl.LOCK_UN )
                self.lock_acquired = False
                log.info( 'Attempting to remove lock file: ' + self.lockfile_name )
                os.remove( self.lockfile_name )
            else:
                log.warn( '__release_lock called but no lock held: ' + self.lockfile_name )
        except Exception as e:
            self.__safe_log( log.error, 'Failed to release lock, error: ' + str( e ) )
            raise
        finally:
            try:
                os.remove( self.lockfile_name )
            except:
                pass
            if getattr( self, 'lock_acquired' ):
                self.lock_acquired = False

    ######################################################################
    # Helper function to process Intellivision faces and store them
    def store_faces( self, media_row, owning_user ):
        log = self.popeye_log

        if 'track_json' not in self.data or not self.data['track_json']:
            log.warning( 'No tracks / faces detected.' )
            return

        log.info( 'Beginning to process store_faces' )

        try:
            tracks = json.loads( self.data['track_json'] )

            if 'tracks' not in tracks or 'numberoftracks' not in tracks['tracks'] or int( tracks['tracks']['numberoftracks'] ) == 0:
                log.warning( 'No tracks / faces detected.' )
                return

            log.info( tracks['tracks']['numberoftracks'] + ' tracks detected.' )

            if int( tracks['tracks']['numberoftracks'] ) == 0:
                log.info( "No face tracks provided." )
                return
            elif int( tracks['tracks']['numberoftracks'] ) == 1:
                log.info( "Handling special case of 1 track." )
                single_track = tracks['tracks']['track']
                if not isinstance( single_track, list ):
                    tracks['tracks']['track'] = [single_track]
                    log.info( "Reformatted data structure for 1 track." )
                else:
                    log.info( 'Tracks was a list despite number of tracks being 1, leaving alone.' )

            # Build up a dictionary of each person with an array of tracks.
            log.debug( 'Building up face track dictionary.' )
            face_tracks = {}
            for track in tracks['tracks']['track']:
                if track['personid'] != None:
                    if track['personid'] in face_tracks:
                        face_tracks[track['personid']].append( track )
                    else:
                        face_tracks[track['personid']] = [ track ]

            # Sort tracks in order of decreasing goodness.
            for face in face_tracks:
                face_tracks[face].sort( key=lambda f: f['recognitionconfidence']*10000+f['detectionscore'] )

            # Build up a dictionary of each person in our database.
            database_contacts = {}
            orm = self.orm
            log.info( 'Getting user id' )
            user_id = owning_user.id
            log.info( 'Getting contacts for user: ' + self.data['info']['uid'] )
            user_contacts = orm.query( Users, Contacts ).filter( and_( Users.id == Contacts.user_id, Users.id == user_id) )
            for user, contact in user_contacts:
                database_contacts[ str( contact.intellivision_id ) ] = {
                    'contact_id' : str( contact.id ),
                    'user'       : user,
                    'contact'    : contact
                    }

            # Iterate through our detected faces.
            for intellivision_id, person_tracks in face_tracks.items():
                contact = None
                if not intellivision_id in database_contacts:
                    log.info( 'Creating new contact for intellivision_id: ' + str( intellivision_id ) )
                    contact = Contacts( uuid             = str( uuid.uuid4() ),
                                        user_id          = user_id,
                                        intellivision_id = intellivision_id )
                else:
                    log.info( 'Detecting existing contact with id: %s for intellivision_id: %s' % ( str( database_contacts[intellivision_id]['contact'].id ), str( intellivision_id ) ) )
                    contact = database_contacts[intellivision_id]['contact']

                contact.picture_uri = person_tracks[0]['bestfaceframe']
            
                for track in person_tracks:
                    track_asset = MediaAssets( uuid       = str( uuid.uuid4() ),
                                               asset_type = 'face',
                                               mimetype   = 'image/jpg',
                                               # DEBUG - reinstate when we get this field populates
                                               # bytes      = track['bytes'],
                                               width      = 500,
                                               height     = 500,
                                               uri        = track['bestfaceframe'],
                                               location   = 'us',
                                               intellivision_file_id = tracks['tracks']['file_id'],
                                               view_count = 0 )
            
                    log.info( 'Adding face asset %s at URI %s' % ( track_asset.uuid, track_asset.uri ) )
                    media_row.assets.append( track_asset )

                    track_feature = MediaAssetFeatures( feature_type           = 'face',
                                                        coordinates            = json.dumps( track ),
                                                        detection_confidence   = track['detectionscore'],
                                                        recognition_confidence = track['recognitionconfidence'] )
                 
                    log.info( 'Adding face feature uuid for contact uuid: %s and asset uuid: %s ' % ( contact.uuid, track_asset.uuid ) )   
                    track_asset.media_asset_features.append( track_feature )
                    contact.media_asset_features.append( track_feature )

        except Exception as e:
            log.error( 'Failed to update faces, error was: ' + str( e ) )
            raise               


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
                               ( label, files[label].get( 'ifile', 'No ifile key' ) ) )
                self.popeye_log.debug( 'Old %s label ofile is: %s' % 
                               ( label, files[label].get( 'ofile', 'No ofile key' ) ) )
                self.popeye_log.debug( 'Old %s label key is: %s' % 
                               ( label, files[label].get( 'key', "No key called 'key'" ) ) )
            else:
                self.popeye_log.info( 'Adding new file label: %s with new values.' % label )

            self.files[label] = { 'ifile' : ifile, 'ofile' : ofile, 'key' : key }

            # self.popeye_log.debug( 'New %s label ifile is: %s' % ( label, ifile ) )
            # self.popeye_log.debug( 'New %s label ofile is: %s' % ( label, ofile ) )
            # self.popeye_log.debug( 'New %s label key is: %s' % ( label, key ) )

            return

        except Exception as e:
            self.__safe_log( self.popeye_log.error, "Exception thrown while adding file: %s" % str( e ) )
            raise

    ######################################################################
    # Utility function to check if a given file exists and is readable
    def __valid_file( self, input_filename ):
        '''Private method: Return true if input_filename exists and is
        readable, and false otherwise.'''
        #self.popeye_log.debug( 'Checking whether file %s exists and is readable.' % input_filename )
        if os.path.isfile( input_filename ):
            #self.popeye_log.debug( 'File %s exists.' % input_filename )

            if os.access( input_filename, os.R_OK ):
                #self.popeye_log.debug( 'File %s exists and is readable.' % input_filename )
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
        self.popeye_log.info( "Set uuid to %s" % self.uuid )

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
                ofile = abs_basename + '_output.mp4', 
                key   = self.uuid + '/' + self.uuid + '.mp4' )
            
            # The 'thumbnail' media file, a jpg.
            self.add_file( 
                label = 'thumbnail',
                ifile = abs_basename+'_output.mp4', 
                ofile = abs_basename+'_thumbnail.jpg', 
                key   = self.uuid + '/' + self.uuid + '_thumbnail.jpg' )
            
            # The 'poster' media file, a jpg.
            self.add_file( 
                label = 'poster',
                ifile = abs_basename+'_output.mp4', 
                ofile = abs_basename+'_poster.jpg', 
                key   = self.uuid + '/' + self.uuid + '_poster.jpg' )
            
            # The 'face' media file, json.
            self.add_file( 
                label = 'face',
                ifile = abs_basename+'_output.mp4', 
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
                ifile = input_filename, 
                ofile = abs_basename+'_exif.json', 
                key   = self.uuid + '/' + self.uuid + '_exif.json' )

            # The 'intellivision' media file, by convention an AVI.
            self.add_file( 
                label = 'intellivision',
                ifile = abs_basename+'_output.mp4', 
                ofile = abs_basename+'.avi', 
                key   = self.uuid + '/' + self.uuid + '.avi' )

            # Self log file.
            self.add_file( 
                label = 'media_log',
                ifile = None, 
                ofile = abs_basename+'.log', 
                key   = None )

        except Exception as e:
            self.__safe_log( self.popeye_log.error, 'Error while initializing files: ' + str( e ) )
            self.handle_errors()
            return 

