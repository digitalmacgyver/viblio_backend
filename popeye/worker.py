import web
import json
import uuid
import hmac
from models import *
import os

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

import sys
import boto
import requests
from boto.s3.key import Key

import helpers
import video_processing
import mimetypes

# Base class for Worker.
from background import Background

# Get filename into defined data structure.
# Get seperate error log for each file along side it.
# Functionize s3 calls
# Put face detection back in with True

class Worker(Background):
    '''The class which drives the video processing pipeline.

    This class is a manager, which maintains some common data
    (e.g. filenames and S3 keys), and which initiates various other
    modules to actually perform the video processing.'''

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

    def __initialize_uuid( self, input_filename ):
        '''Private method: We expect an input filename that is the
        UUID of the media file that has been uploaded.  We store this
        value in self.uuid.
        '''
        self.__valid_file( input_filename )
        self.uuid = os.path.splitext( os.path.basename( input_filename ) )[0]
        self.log.info( "Set uuid to %s" % self.uuid )

    def __valid_file( self, input_filename ):
        '''Private method: Return true if input_filename exists and is
        readable, and false otherwise.'''
        self.log.info( 'Checking whether file %s exists and is readable.' % input_filename )
        if os.path.isfile( input_filename ):
            self.log.info( 'File %s exists.' % input_filename )

            if os.access( input_filename, os.R_OK ):
                self.log.info( 'File %s is readable.' % input_filename )
                return True
            else:
                self.log.error( 'File %s is not readable.' % input_filename )
                return False
        else:
            self.log.error( 'File %s does not exist.' % input_filename )
            return False

    def __safe_log( logger, message ):
        '''Private method: Used for when we are trying to log in an
        exception block - in this case we want to be careful to not
        blow out our error handling code due to a problem with
        logging.'''
        try:
            logger( message )
        except Exception as e:
            print "Exception thrown while logging error:" % str( e )

        return

    def add_file( self, label, ifile=None, ofile=None, key=None ):
        '''Public method: Attempt to add files[label] = { ifile,
        ofile, key } to the files data structure.
        '''
        try:
            if label in self.files:
                self.log.info( 'Overwriting existing file label: %s with new values.' % label )
                self.log.info( 'Old %s label ifile is: %s' % 
                               ( label, files[label].get( 'ifile', 'No ifile key' ) ) )
                self.log.info( 'Old %s label ofile is: %s' % 
                               ( label, files[label].get( 'ofile', 'No ofile key' ) ) )
                self.log.info( 'Old %s label key is: %s' % 
                               ( label, files[label].get( 'key', "No key called 'key'" ) ) )
            else:
                self.log.info( 'Adding new file label: %s with new values.' % label )

            self.files[label] = { 'ifile' : ifile, 'ofile' : ofile, 'key' : key }

            self.log.info( 'New %s label ifile is: %s' % ( label, ifile ) )
            self.log.info( 'New %s label ofile is: %s' % ( label, ofile ) )
            self.log.info( 'New %s label key is: %s' % ( label, key ) )

            return

        except Exception as e:
            self.__safe_log( self.log.error, "Exception thrown while adding file: %s" % str( e ) )
            raise

    def __initialize_files( self, input_filename ):
        '''Private method: Populate the files data structure for the
        worker class.  Files is a dictionary where:

        * Each key corresponds to a type of file in the video
          processing pipeline (e.g. original, mp4, thumbnail, etc.)

        * Each value is itself a dictionary, with the following keys
          as appropriate:
          + ifile - the full filesystem path of the input to this
            stage of the pipeline

          + ofile - the full filesystem path of the output of this
            stage of the pipeline

          + key - the key that the output resource will be associated
            with in persistent storage (currently S3)
            
          No exception handling - if something goes wrong here we
          can't proceed reasonably.
          '''
        self.files = {}
        
        abs_basename = os.path.splitext( input_filename )
        
        # The 'main' media file, an mp4.
        self.add_file( 
            label = 'main',
            ifile = input_filename, 
            ofile = abs_basename+'.mp4', 
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
            key   = None )

        # The 'exif' media file, json
        self.add_file( 
            label = 'exif',
            ifile = input_filename, 
            ofile = abs_basename+'_exif.json', 
            key   = self.uuid + '/' + self.uuid + '_exif.json' )

        # The 'intellivision' media file, by convention an AVI.
        self.add_file( 
            label = 'intellivision',
            ifile = abs_basename+'.mp4', 
            ofile = abs_basename+'.avi', 
            key   = self.uuid + '/' + self.uuid + '.avi' )

    # DEBUG - search code for info.
    def __initialize_info( self, ifile ):
        '''Load the contents of the info input file into the info field from
        JSON'''
        try:
            f = open( ifile )
            self.info = json.load( f )
        except Exception as e:
            log.error( 'Failed to open and parse as JSON: %s error was: %s' % ( ifile, str( e ) ) )
            self.handle_errors()
            raise

    # DEBUG - search code for md.
    def __initialize_metadata( self, ifile ):
        '''Load the contents of the metadata input file into the
        metadata field from JSON'''
        try:
            f = open( ifile )
            self.metadata = json.load( f )
        except Exception as e:
            log.error( 'Failed to open and parse %s as JSON error was %s' % ( ifile, str( e ) ) )
            self.handle_errors()
            raise

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

        # Convienience variables.
        files = self.files
        log   = self.log
        orm   = self.orm

        log.info( 'Worker.py, starting to process: ' + self.uuid )

        # Extract relevant EXIF data using exiftool
        exif = self.__safe_call( helpers.exif( ifile=files['exif']['ifile'], ofile=files['exif']['ofile'], log ) )
        log.info( 'EXIF data extracted: ' + str( exif ) )

        # Verify the inintial inputs we expect are valid.
        for label in [ 'main', 'info', 'metadata' ]:
            if not self.__valid_file( files[label]['ifile'] ):
                log.error( 'File %s does not exist for label %s' % ( files[label]['ifile'], label ) )
                self.handle_errors()
                return
            else:
                log.info( '%s input file validated.' % label )

        log.info( 'Initializing info field from JSON file: ' + files['info']['ifile'] )
        self.__initialize_info( self.info, files['info']['ifile'] )
        log.info( 'info field is: ' + json.dumps( self.info ) )

        log.info( 'Initializing metadata field from JSON file: ' + files['metadata']['ifile'] )
        self.__initialize_metadata( self.metadata, files['metadata']['ifile'] )
        log.info( 'metadata field is: ' + json.dumps( self.metadata ) )


        log.info( 'Renaming input file %s with lower cased file extension based on uploader information' % files['main']['input'] )
        try:
            new_filename = helpers.rename_upload_with_extension( files['main'], self.info, log )
        except Exception as e:
            log.error( 'Could not rename input file, error was: ' + e )
        finally:
            self.handle_errors()
        log.info( 'Renamed input file is: ' new_filename )

        # Get the mimetype of the video file
        mimetype, uu = mimetypes.guess_type( c['video']['input'] )

        # Transcode to mp4 and rotate if necessary. Also, relocate moov atom for immediate playback
        video_processing.transcode(c, mimetype, exif['rotation'])

        # Generate poster and thumbnails.
        video_processing.generate_poster(c['poster']['input'], c['poster']['output'], exif['rotation'], exif['width'],exif['height'])
        video_processing.generate_thumbnail(c['thumbnail']['input'], c['thumbnail']['output'], exif['rotation'], exif['width'],exif['height'])

        # The face - The strange boolean structure here allows us to
        # easily turn it on and off.
        found_faces = False
        if found_faces:
            cmd = 'python /viblio/bin/extract_face.py %s %s' % ( c['face']['input'], c['face']['output'] )
            log.info( cmd )
            found_faces = True
            if not os.system( cmd ) == 0:
                found_faces = False
                log.error( 'Failed to find any faces in video for command: %s' % cmd )

        ######################################################################
        # Upload to S3
        #
        try:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            bucket = s3.get_bucket(config.bucket_name)
            bucket_contents = Key(bucket)
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to obtain s3 bucket: %s' % str( e ) )
            return

        log.info( 'Uploading to s3: %s' % c['video']['output'] )
        try:
            bucket_contents.key = c['video_key']
            bucket_contents.set_contents_from_filename( c['video']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        log.info( 'Uploading to s3: %s' % c['avi']['output'] )
        try:
            bucket_contents.key = c['avi_key']
            bucket_contents.set_contents_from_filename( c['avi']['output'] )
            bucket_contents.make_public()
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return
        
        log.info( 'Uploading to s3: %s' % c['thumbnail']['output'] )
        try:
            bucket_contents.key = c['thumbnail_key']
            bucket_contents.set_contents_from_filename( c['thumbnail']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        log.info( 'Uploading to s3: %s' % c['poster']['output'] )
        try:
            bucket_contents.key = c['poster_key']
            bucket_contents.set_contents_from_filename( c['poster']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
        try:
            bucket_contents.key = c['metadata_key']
            bucket_contents.set_contents_from_filename( c['metadata']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        log.info( 'Uploading to s3: %s' % c['exif']['output'] )
        try:
            bucket_contents.key = c['exif_key']
            bucket_contents.set_contents_from_filename( c['exif']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        if found_faces:
            log.info( 'Uploading to s3: %s' % c['face']['output'] )
            try:
                bucket_contents.key = c['face_key']
                bucket_contents.set_contents_from_filename( c['face']['output'] )
            except Exception as e:
                self.handle_errors( c )
                log.error( 'Failed to upload to s3: %s' % str( e ) )
                return

        log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
        try:
            bucket_contents.key = c['metadata_key']
            bucket_contents.set_contents_from_filename( c['metadata']['output'] )
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to upload to s3: %s' % str( e ) )
            return

        #######################################################################
        # DATABASE
        #
        # Default the filename, then try to obtain it from the
        # client side metadata.

        # Get the client metadata too.  It includes the original file's
        # filename for instance...
        if os.path.isfile( c['metadata']['input'] ):
            try:
                f = open( c['metadata']['input'] )
                md = json.load( f )
            except Exception as e:
                self.handle_errors( c )
                log.error( 'Failed to parse %s error was %s' % ( c['metadata']['input'], str( e ) ) )
                return

        filename = os.path.basename( c['video']['input'] )
        if md and md['file'] and md['file']['Path']:
            filename = md['file']['Path']

        # Add the mediafile to the database
        data = {
            'uuid': c['uuid'],
            'user_id': info['uid'],
            'filename': filename,
            'mimetype': mimetype,
            'uri': c['video_key'],
            'size': os.path.getsize( c['video']['output'] )
            }

        try:
            media = Media( uuid=data['uuid'],
                           media_type='original',
                           recording_date=exif['create_date'],
                           lat=exif['lat'],
                           lng=exif['lng'],
                           filename=data['filename'] )
            # main
            asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='main',
                                mimetype=data['mimetype'],
                                metadata_uri=c['metadata_key'],
                                bytes=data['size'],
                                uri=data['uri'],
                                location='us' )
            media.assets.append( asset )

            # AVI
            avi_asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='intellivision',
                                mimetype='video/avi',
                                bytes=os.path.getsize( c['avi']['output'] ),
                                uri=c['avi_key'],
                                location='us' )
            media.assets.append( avi_asset )

            # thumbnail
            asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='thumbnail',
                                mimetype='image/jpg',
                                bytes=os.path.getsize( c['thumbnail']['output'] ),
                                width=128, height=128,
                                uri=c['thumbnail_key'],
                                location='us' )
            media.assets.append( asset )

            # poster
            poster_asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='poster',
                                mimetype='image/jpg',
                                bytes=os.path.getsize( c['poster']['output'] ),
                                width=320, height=240,
                                uri=c['poster_key'],
                                location='us' )
            media.assets.append( poster_asset )

            # face
            if found_faces:

                log.info( 'Face detected' )

                asset = MediaAssets( uuid=str(uuid.uuid4()),
                                     asset_type='face',
                                     mimetype='image/jpg',
                                     bytes=os.path.getsize( c['face']['output'] ),
                                     width=128, height=128,
                                     uri=c['face_key'],
                                     location='us' )
                media.assets.append( asset )

            # Try to obtain the user from the database
            try:
                user = orm.query( Users ).filter_by( uuid = info['uid'] ).one()
            except Exception as e:
                self.handle_errors( c )
                log.error( 'Failed to look up user by uuid: %s error was %s' % ( info['uid'], str( e ) ) )
                return

            user.media.append( media )

            # DEBUG Test adding a feature.
            #log.info( 'Adding a feature to the poster.' )
            #
            #row = MediaAssetFeatures( feature_type = 'face',
            #                          detection_confidence = 3.14159
            #                          )
            #poster_asset.media_asset_features.append( row )

            #raise Exception('Oops!')
            

        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to add mediafile to database!: %s' % str( e ) )
            return

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.handle_errors( c )
            log.error( 'Failed to commit the database: %s' % str( e ) )
            return

        #######################################################################
        # Send notification to CAT server.
        #######################################################################
        data['location'] = 'us'
        data['bucket_name'] = config.bucket_name
        data['uid'] = data['user_id']
        try:
            log.info( 'Notifying Cat server at %s' %  config.viblio_server_url )
            site_token = hmac.new( config.site_secret, data['user_id']).hexdigest()
            res = requests.get(config.viblio_server_url, params={ 'uid': data['user_id'], 'mid': data['uuid'], 'site-token': site_token })
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
            self.handle_errors( c )
            log.error( 'Failed to notify Cat: %s' % str( e ) )
            return

        ######################################################################
        # Cleanup files on success.
        ######################################################################
        try:
            log.info( 'File successfully processed, removing temp files ...' )
            for f in ['video','thumbnail','poster','metadata','face','exif','avi']:
                if ( f in c ) and ( 'output' in c[f] ) and os.path.isfile( c[f]['output'] ):
                    os.remove( c[f]['output'] )
                if ( f in c ) and ( 'input' in c[f] ) and os.path.isfile( c[f]['input'] ):
                    os.remove( c[f]['input'] )
            os.remove( c['info'] )
        except Exception as e_inner:
            self.handle_errors( c )
            log.error( 'Some trouble removing temp files: %s' % str( e_inner ) )

        log.info( 'DONE WITH %s' % c['uuid'] )

        return

    def handle_errors( self, filenames ):
        '''Copy temporary files to error directory.'''
        try:
            log = self.log
            log.info( 'Error occured, relocating temp files to error directory...' )
            for f in ['video','thumbnail','poster','metadata','face','exif','avi']:
                if ( f in filenames ) and ( 'output' in filenames[f] ) and os.path.isfile( filenames[f]['output'] ):
                    full_name = filenames[f]['output']
                    base_path = os.path.split( full_name )[0]
                    file_name = os.path.split( full_name )[1]
                    os.rename( filenames[f]['output'], base_path + '/errors/' + file_name )
                if ( f in filenames ) and ( 'input' in filenames[f] ) and os.path.isfile( filenames[f]['input'] ):
                    full_name = filenames[f]['input']
                    base_path = os.path.split( full_name )[0]
                    file_name = os.path.split( full_name )[1]
                    os.rename( filenames[f]['input'], base_path + '/errors/' + file_name )
            if 'info' in filenames:
                full_name = filenames['info']
                base_path = os.path.split( full_name )[0]
                file_name = os.path.split( full_name )[1]
                os.rename( filenames['info'], base_path + '/errors/' + file_name )
        except Exception as e_inner:
            try:
                log = self.log
                log.error( 'Some trouble relocating temp files temp files: %s' % str( e_inner ) )
            except:
                pass
