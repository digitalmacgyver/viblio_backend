import web
import json
from models import *
import os

from config import Config
config = Config( 'popeye.cfg' )

import sys
import boto
import requests
from boto.s3.key import Key

import mimetypes

def perror( msg ):
    print msg
    return { 'error': True, 'message': msg }

def process_video( c, orm ):
    
    # If the main input file (video) is not present we're toast
    if not os.path.isfile( c['video']['input'] ):
        return perror( 'File does not exist: %s' % c['video']['input'] )

    # We need the brewtus metadata too
    if not os.path.isfile( c['info'] ):
        return perror( 'File does not exist: %s' % c['info'] )

    # Get the brewtus info
    try:
        f = open( c['info'] )
        info = json.load( f )
    except Exception, e:
        return perror( 'Failed to open and parse %s' % c['info'] )

    # Get the mimetype of the video file
    mimetype, uu = mimetypes.guess_type( c['video']['input'] )

    # If the input video is not mp4, then transcode it into mp4
    if not mimetype == 'video/mp4':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -movflags faststart -i %s %s' % ( c['video']['input'], c['video']['output'] )
        print cmd
        if not os.system( cmd ) == 0:
            return perror( 'Failed to execute: %s' % cmd )

        mimetype = 'video/mp4'
    else:
        c['video']['output'] = c['video']['input']

    # Generate the poster
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -f image2 -s 320x240 %s' % ( c['poster']['input'], c['poster']['output'] )
    print cmd
    if not os.system( cmd ) == 0:
        return perror( 'Failed to execute: %s' % cmd )

    # The thumbnail
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -f image2 -s 128x128 %s' % ( c['thumbnail']['input'], c['thumbnail']['output'] )
    print cmd
    if not os.system( cmd ) == 0:
        return perror( 'Failed to execute: %s' % cmd )

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
        return perror( 'Failed to obtain s3 bucket: %s' % e.message )

    print 'Uploading to s3: %s' % c['video']['output']
    try:
        bucket_contents.key = video_key
        bucket_contents.set_contents_from_filename( c['video']['output'] )
    except Exception, e:
        return perror( 'Failed to upload to s3: %s' % e.message )

    print 'Uploading to s3: %s' % c['thumbnail']['output']
    try:
        bucket_contents.key = thumbnail_key
        bucket_contents.set_contents_from_filename( c['thumbnail']['output'] )
    except Exception, e:
        return perror( 'Failed to upload to s3: %s' % e.message )

    print 'Uploading to s3: %s' % c['poster']['output']
    try:
        bucket_contents.key = poster_key
        bucket_contents.set_contents_from_filename( c['poster']['output'] )
    except Exception, e:
        return perror( 'Failed to upload to s3: %s' % e.message )

    print 'Uploading to s3: %s' % c['metadata']['output']
    try:
        bucket_contents.key = metadata_key
        bucket_contents.set_contents_from_filename( c['metadata']['output'] )
    except Exception, e:
        return perror( 'Failed to upload to s3: %s' % e.message )

    # Add the mediafile to the database
    data = {
        'uuid': c['uuid'],
        'user_id': info['uid'],
        'filename': os.path.basename( c['video']['input'] ),
        'mimetype': mimetype,
        'uri': video_key,
        'size': os.path.getsize( c['video']['output'] )
        }

    try:
        # filename, uuid, user_id, mimetype, size, uri
        print 'Adding DB record ...'
        mediafile = Video( 
            filename=data['filename'],
            uuid=data['uuid'],
            user_id=data['user_id'],
            mimetype=data['mimetype'],
            size=data['size'],
            uri=data['uri']
            )
        orm.add( mediafile )
    except Exception, e:
        return perror( 'Failed to add mediafile to database!: %s' % e.message )

    # And finally, notify the Cat server
    data['location'] = 'us'
    try:
        print 'Notifying Cat server ...'
        res = requests.get(config.viblio_server_url, params=data)
    except Exception, e:
        return perror( 'Failed to notify Cat: %s' % e.message )

    # Remove all local files
    try:
        print 'Removing temp files ...'
        for f in ['video','thumbnail','poster','metadata']:
            if os.path.isfile( c[f]['output'] ):
                os.remove( c[f]['output'] )
            if os.path.isfile( c[f]['input'] ):
                os.remove( c[f]['input'] )
        os.remove( c['info'] )
    except Exception, e:
        print 'Some trouble removing temp files: %s' % e.message

    print 'DONE WITH %s' % c['uuid']
    return {}

