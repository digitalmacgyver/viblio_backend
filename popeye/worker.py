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

from background import Background

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

class Worker(Background):
    def run(self):
        orm = self.orm
        log = self.log
        full_filename = self.data['full_filename']

        log.info( 'Worker.py, starting to process: ' + full_filename )
        c = helpers.create_filenames( full_filename )

        # Extract relevant EXIF data using exiftool
        exif = helpers.exif(c)
        log.info( 'EXIF data extracted: ' + str(exif))

        # If the main input file (video) is not present we're toast
        if not os.path.isfile( c['video']['input'] ):
            self.handle_errors( c )
            return perror( log,  'File does not exist: %s' % c['video']['input'] )

        # We need the brewtus metadata too
        if not os.path.isfile( c['info'] ):
            self.handle_errors( c )
            return perror( log,  'File does not exist: %s' % c['info'] )

        # Get the brewtus info
        try:
            f = open( c['info'] )
            info = json.load( f )
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to open and parse %s error was %s' % ( c['info'], str( e ) ) )

        # Get the client metadata too.  It includes the original file's
        # filename for instance...
        if os.path.isfile( c['metadata']['input'] ):
            try:
                f = open( c['metadata']['input'] )
                md = json.load( f )
            except Exception as e:
                self.handle_errors( c )
                return perror( log,  'Failed to parse %s error was %s' % ( c['metadata']['input'], str( e ) ) )

        # Try to obtain the user from the database
        try:
            user = orm.query( Users ).filter_by( uuid = info['uid'] ).one()
        except Exception as e:
            self.handle_errors( c )
            return perror( log, 'Failed to look up user by uuid: %s error was %s' % ( info['uid'], str( e ) ) )

        # Brewtus writes the uploaded file as <fileid> without an extenstion,
        # but the info struct has an extenstion.  See if its something other than
        # '' and if so, move the file under its extension so transcoding works.
        if 'fileExt' in info:
            src = c['video']['input']
            tar = src + info['fileExt'].lower()
            if not src == tar:
                if not os.system( "/bin/mv %s %s" % ( src, tar ) ) == 0:
                    self.handle_errors( c )
                    return perror( log,  "Failed to execute: /bin/mv %s %s" % ( src, tar ) )
                c['video']['input'] = tar

        # Get the mimetype of the video file
        mimetype, uu = mimetypes.guess_type( c['video']['input'] )

        # Transcode to mp4 and rotate if necessary. Also, relocate moov atom for immediate playback
        video_processing.transcode(c, mimetype, exif['rotation'])

        # Generate poster and thumbnails.
        video_processing.generate_poster(c['poster']['input'], c['poster']['output'], exif['rotation'], exif['width'],exif['height'])
        video_processing.generate_thumbnail(c['thumbnail']['input'], c['thumbnail']['output'], exif['rotation'], exif['width'],exif['height'])

        # The face - The strange boolean structure here allows us to
        # easily turn it on and off.
        found_faces = True
        if found_faces:
            cmd = 'python /viblio/bin/extract_face.py %s %s' % ( c['face']['input'], c['face']['output'] )
            log.info( cmd )
            found_faces = True
            if not os.system( cmd ) == 0:
                found_faces = False
                perror( log,  'Failed to find any faces in video for command: %s' % cmd )

        ######################################################################
        # Upload to S3
        #
        try:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            bucket = s3.get_bucket(config.bucket_name)
            bucket_contents = Key(bucket)
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to obtain s3 bucket: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['video']['output'] )
        try:
            bucket_contents.key = c['video_key']
            bucket_contents.set_contents_from_filename( c['video']['output'] )
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['avi']['output'] )
        try:
            bucket_contents.key = c['avi_key']
            bucket_contents.set_contents_from_filename( c['avi']['output'] )
            bucket_contents.make_public()
        except Exception as e:
            self.handle_errors( c )
            return perror( log, 'Failed to upload to s3: %s' % str( e ) )
        
        log.info( 'Uploading to s3: %s' % c['thumbnail']['output'] )
        try:
            bucket_contents.key = c['thumbnail_key']
            bucket_contents.set_contents_from_filename( c['thumbnail']['output'] )
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['poster']['output'] )
        try:
            bucket_contents.key = c['poster_key']
            bucket_contents.set_contents_from_filename( c['poster']['output'] )
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
        try:
            bucket_contents.key = c['metadata_key']
            bucket_contents.set_contents_from_filename( c['metadata']['output'] )
        except Exception as e:
            helpers.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['exif']['output'] )
        try:
            bucket_contents.key = c['exif_key']
            bucket_contents.set_contents_from_filename( c['exif']['output'] )
        except Exception as e:
            helpers.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        if found_faces:
            log.info( 'Uploading to s3: %s' % c['face']['output'] )
            try:
                bucket_contents.key = c['face_key']
                bucket_contents.set_contents_from_filename( c['face']['output'] )
            except Exception as e:
                self.handle_errors( c )
                return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
        try:
            bucket_contents.key = c['metadata_key']
            bucket_contents.set_contents_from_filename( c['metadata']['output'] )
        except Exception as e:
            self.handle_errors( c )
            return perror( log,  'Failed to upload to s3: %s' % str( e ) )

        #######################################################################
        # DATABASE
        #
        # Default the filename, then try to obtain it from the
        # client side metadata.
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
            return perror( log,  'Failed to add mediafile to database!: %s' % str( e ) )

        # Commit to database.
        try:
            orm.commit()
        except Exception as e:
            self.handle_errors( c )
            return perror( log, 'Failed to commit the database: %s' % str( e ) )

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
            return perror( log,  'Failed to notify Cat: %s' % str( e ) )

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

        return {}

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
