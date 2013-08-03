import web
import json
from models import *
import os

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

import sys
import boto
import requests
from boto.s3.key import Key

import mimetypes

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

def process_video( c, orm, log ):

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
    #ffopts = '-strict -2'
    ffopts = ''
    if not mimetype == 'video/mp4':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( c['video']['input'], ffopts, c['video']['output'] )
        log.info( cmd )
        if not os.system( cmd ) == 0:
            return perror( log,  'Failed to execute: %s' % cmd )

        # Move the metadata atom(s) to the front of the file.  -movflags faststart is
        # not a valid option in our version of ffmpeg, so cannot do it there.  qt-faststart
        # is broken.  qtfaststart is a python based solution that has worked much better for me
        cmd = '/usr/local/bin/qtfaststart %s' % c['video']['output']
        log.info( cmd )
        if not os.system( cmd ) == 0:
            perror( log,  'Failed to run qtfaststart on the output file' )

        mimetype = 'video/mp4'
    else:
        c['video']['output'] = c['video']['input']

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

    # Upload to S3
    video_key      = c['uuid'] + '/' + os.path.basename( c['video']['output'] )
    thumbnail_key  = c['uuid'] + '/' + os.path.basename( c['thumbnail']['output'] )
    poster_key     = c['uuid'] + '/' + os.path.basename( c['poster']['output'] )
    metadata_key   = c['uuid'] + '/' + os.path.basename( c['metadata']['output'] )

    try:
        s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
        bucket = s3.get_bucket(config.bucket_name)
        bucket_contents = Key(bucket)
    except Exception, e:
        return perror( log,  'Failed to obtain s3 bucket: %s' % e.message )

    log.info( 'Uploading to s3: %s' % c['video']['output'] )
    try:
        bucket_contents.key = video_key
        bucket_contents.set_contents_from_filename( c['video']['output'] )
    except Exception, e:
        return perror( log,  'Failed to upload to s3: %s' % e.message )

    log.info( 'Uploading to s3: %s' % c['thumbnail']['output'] )
    try:
        bucket_contents.key = thumbnail_key
        bucket_contents.set_contents_from_filename( c['thumbnail']['output'] )
    except Exception, e:
        return perror( log,  'Failed to upload to s3: %s' % e.message )

    log.info( 'Uploading to s3: %s' % c['poster']['output'] )
    try:
        bucket_contents.key = poster_key
        bucket_contents.set_contents_from_filename( c['poster']['output'] )
    except Exception, e:
        return perror( log,  'Failed to upload to s3: %s' % e.message )

    log.info( 'Uploading to s3: %s' % c['metadata']['output'] )
    try:
        bucket_contents.key = metadata_key
        bucket_contents.set_contents_from_filename( c['metadata']['output'] )
    except Exception, e:
        return perror( log,  'Failed to upload to s3: %s' % e.message )

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
        # filename, uuid, user_id, mimetype, size, uri
        log.info( 'Adding DB record ...' )
        mediafile = Video( 
            filename=data['filename'],
            uuid=data['uuid'],
            user_id=data['user_id'],
            mimetype=data['mimetype'],
            size=data['size'],
            uri=data['uri']
            )
        orm.add( mediafile )
        orm.commit()
    except Exception, e:
        return perror( log,  'Failed to add mediafile to database!: %s' % e.message )

    # And finally, notify the Cat server
    data['location'] = 'us'
    data['bucket_name'] = config.bucket_name
    data['uid'] = data['user_id']
    try:
        log.info( 'Notifying Cat server ...' )
        res = requests.get(config.viblio_server_url, params=data)
        jdata = json.loads( res.text )
        if 'error' in jdata:
            raise Exception( jdata['message'] )
    except Exception, e:
        return perror( log,  'Failed to notify Cat: %s' % e.message )

    # Remove all local files
    try:
        log.info( 'Removing temp files ...' )
        for f in ['video','thumbnail','poster','metadata']:
            if os.path.isfile( c[f]['output'] ):
                os.remove( c[f]['output'] )
            if os.path.isfile( c[f]['input'] ):
                os.remove( c[f]['input'] )
        os.remove( c['info'] )
    except Exception, e:
        log.error( 'Some trouble removing temp files: %s' % str(e) )

    log.info( 'DONE WITH %s' % c['uuid'] )
    return {}

