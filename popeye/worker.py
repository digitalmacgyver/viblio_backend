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

import mimetypes

from background import Background

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

class Worker(Background):
    def run(self):
        orm = self.orm
        log = self.log
        c   = self.data

        # If the main input file (video) is not present we're toast
        if not os.path.isfile( c['video']['input'] ):
            return perror( log,  'File does not exist: %s' % c['video']['input'] )

        # We need the brewtus metadata too
        if not os.path.isfile( c['info'] ):
            return perror( log,  'File does not exist: %s' % c['info'] )

        # Get the brewtus info
        try:
            f = open( c['info'] )
            info = json.load( f )
        except Exception, e:
            return perror( log,  'Failed to open and parse %s' % c['info'] )

        # Get the client metadata too.  It includes the original file's
        # filename for instance...
        if os.path.isfile( c['metadata']['input'] ):
            try:
                f = open( c['metadata']['input'] )
                md = json.load( f )
            except Exception, e:
                perror( log,  'Failed to parse %s' % c['metadata']['input'] )

        # Try to obtain the user from the database
        try:
            user = orm.query( Users ).filter_by( uuid = info['uid'] ).one()
        except Exception, e:
            return perror( log, 'Failed to look up user by uuid: %s: %s' % ( info['uid'], str(e) ) )

        # Brewtus writes the uploaded file as <fileid> without an extenstion,
        # but the info struct has an extenstion.  See if its something other than
        # '' and if so, move the file under its extension so transcoding works.
        if 'fileExt' in info:
            src = c['video']['input']
            tar = src + info['fileExt']
            if not src == tar:
                if not os.system( "/bin/mv %s %s" % ( src, tar ) ) == 0:
                    return perror( log,  "Failed to execute: /bin/mv %s %s" % ( src, tar ) )
                c['video']['input'] = tar

        # Get the mimetype of the video file
        mimetype, uu = mimetypes.guess_type( c['video']['input'] )

        # If the input video is not mp4, then transcode it into mp4
        ffopts = ''
        if not mimetype == 'video/mp4':
            cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( c['video']['input'], ffopts, c['video']['output'] )
            log.info( cmd )
            if not os.system( cmd ) == 0:
                return perror( log,  'Failed to execute: %s' % cmd )
            mimetype = 'video/mp4'
        else:
            c['video']['output'] = c['video']['input']

        if mimetype == 'video/mp4':
            # Move the metadata atom(s) to the front of the file.  -movflags faststart is
            # not a valid option in our version of ffmpeg, so cannot do it there.  qt-faststart
            # is broken.  qtfaststart is a python based solution that has worked much better for me
            cmd = '/usr/local/bin/qtfaststart %s' % c['video']['output']
            log.info( cmd )
            if not os.system( cmd ) == 0:
                perror( log,  'Failed to run qtfaststart on the output file' )

        # Generate the poster
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -f image2 -s 320x240 %s' % ( c['poster']['input'], c['poster']['output'] )
        log.info( cmd )
        if not os.system( cmd ) == 0:
            return perror( log,  'Failed to execute: %s' % cmd )

        # The thumbnail
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -f image2 -s 128x128 %s' % ( c['thumbnail']['input'], c['thumbnail']['output'] )
        log.info( cmd )
        if not os.system( cmd ) == 0:
            return perror( log,  'Failed to execute: %s' % cmd )

        # The face
        cmd = 'python /viblio/bin/extract_face.py %s %s' % ( c['face']['input'], c['face']['output'] )
        log.info( cmd )
        found_faces = True
        if not os.system( cmd ) == 0:
            found_faces = False
            perror( log,  'Failed to find any faces in video for command: %s' % cmd )

        video_key      = c['uuid'] + '/' + os.path.basename( c['video']['output'] )
        thumbnail_key  = c['uuid'] + '/' + os.path.basename( c['thumbnail']['output'] )
        poster_key     = c['uuid'] + '/' + os.path.basename( c['poster']['output'] )
        metadata_key   = c['uuid'] + '/' + os.path.basename( c['metadata']['output'] )
        face_key       = c['uuid'] + '/' + os.path.basename( c['face']['output'] ) 

        ###########################################################################
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
            'uri': video_key,
            'size': os.path.getsize( c['video']['output'] )
            }

        try:
            media = Media( uuid=data['uuid'],
                           media_type='original',
                           filename=data['filename'] )

            # main
            asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='main',
                                mimetype=data['mimetype'],
                                metadata_uri=metadata_key,
                                bytes=data['size'],
                                uri=data['uri'],
                                location='us' )
            media.assets.append( asset )

            # thumbnail
            asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='thumbnail',
                                mimetype='image/jpg',
                                bytes=os.path.getsize( c['thumbnail']['output'] ),
                                width=128, height=128,
                                uri=thumbnail_key,
                                location='us' )
            media.assets.append( asset )

            # poster
            asset = MediaAssets( uuid=str(uuid.uuid4()),
                                asset_type='poster',
                                mimetype='image/jpg',
                                bytes=os.path.getsize( c['poster']['output'] ),
                                width=320, height=240,
                                uri=poster_key,
                                location='us' )
            media.assets.append( asset )

            # face
            if found_faces:
                asset = MediaAssets( uuid=str(uuid.uuid4()),
                                     asset_type='face',
                                     mimetype='image/jpg',
                                     bytes=os.path.getsize( c['face']['output'] ),
                                     width=128, height=128,
                                     uri=face_key,
                                     location='us' )
                media.assets.append( asset )

            user.media.append( media )

        except Exception, e:
            # Remove all local files
            try:
                log.info( 'Removing temp files ...' )
                for f in ['video','thumbnail','poster','metadata','face']:
                    if os.path.isfile( c[f]['output'] ):
                        os.remove( c[f]['output'] )
                    if os.path.isfile( c[f]['input'] ):
                        os.remove( c[f]['input'] )
                os.remove( c['info'] )
            except Exception, e:
                log.error( 'Some trouble removing temp files: %s' % str(e) )

            return perror( log,  'Failed to add mediafile to database!: %s' % str(e) )

        ###########################################################################

        # Upload to S3
        #
        try:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            bucket = s3.get_bucket(config.bucket_name)
            bucket_contents = Key(bucket)
        except Exception, e:
            return perror( log,  'Failed to obtain s3 bucket: %s' % str(e) )

        log.info( 'Uploading to s3: %s' % c['video']['output'] )
        try:
            bucket_contents.key = video_key
            bucket_contents.set_contents_from_filename( c['video']['output'] )
        except Exception, e:
            return perror( log,  'Failed to upload to s3: %s' % str(e) )

        log.info( 'Uploading to s3: %s' % c['thumbnail']['output'] )
        try:
            bucket_contents.key = thumbnail_key
            bucket_contents.set_contents_from_filename( c['thumbnail']['output'] )
        except Exception, e:
            return perror( log,  'Failed to upload to s3: %s' % str(e) )

        log.info( 'Uploading to s3: %s' % c['poster']['output'] )
        try:
            bucket_contents.key = poster_key
            bucket_contents.set_contents_from_filename( c['poster']['output'] )
        except Exception, e:
            return perror( log,  'Failed to upload to s3: %s' % str(e) )

        if found_faces:
            log.info( 'Uploading to s3: %s' % c['face']['output'] )
            try:
                bucket_contents.key = face_key
                bucket_contents.set_contents_from_filename( c['face']['output'] )
            except Exception, e:
                return perror( log,  'Failed to upload to s3: %s' % str(e) )

        log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
        try:
            bucket_contents.key = metadata_key
            bucket_contents.set_contents_from_filename( c['metadata']['output'] )
        except Exception, e:
            return perror( log,  'Failed to upload to s3: %s' % str(e) )

        # We're OK with S3, lets commit the database.
        try:
            orm.commit()
        except Exception, e:
            return perror( log, 'Failed to commit the database: %s' % str(e) )

        # And finally, notify the Cat server
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
        except Exception, e:
            perror( log,  'Failed to notify Cat: %s' % str(e) )

        # Remove all local files
        try:
            log.info( 'Removing temp files ...' )
            for f in ['video','thumbnail','poster','metadata','face']:
                if os.path.isfile( c[f]['output'] ):
                    os.remove( c[f]['output'] )
                if os.path.isfile( c[f]['input'] ):
                    os.remove( c[f]['input'] )
            os.remove( c['info'] )
        except Exception, e:
            log.error( 'Some trouble removing temp files: %s' % str(e) )

        log.info( 'DONE WITH %s' % c['uuid'] )
        return {}

