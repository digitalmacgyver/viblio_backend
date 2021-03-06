#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
import datetime
import json
import hmac
import logging
from logging import handlers
import os
import requests
from sqlalchemy import and_
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3
import vib.db.orm
from vib.db.models import *

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'greet_new_users: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def welcome_video_for_user( user_uuid, video_file, poster_file, poster_animated=None, thumbnail_file=None, face_files=[], image_files=[], **options ):
    '''Adds the video, thumbnail, and poster for the user_uuid.
    
    Each of the video, poster, and thumbanil _file arguments is a dictionary with:
    * s3_bucket
    * s3_key
    * bytes
    * format
    keys

    The face_files argument is a list, each element is a dictionary with:
    * s3_bucket
    * s3_key
    * bytes
    * format
    * face_mimetype      - 'image/png'
    * face_size          - '128x128'
    * contact_name       - 'VIBLIO Feedback'
    * contact_email      - 'feedback@viblio.com'

    Optional keyword arguments exist with the following defaults: 
 
    * description        - 'VIBLIO lets you use the power of video to build strong personal connections.  Keep your memories in motion - with VIBLIO.'
    * filename           - ''
    * geo_address        - '1561-1599 Middlefield Road, Palo Alto, CA 94301, USA'
    * geo_city           - 'Palo Alto'
    * lat                - 37.442174
    * lng                - -122.143199
    * poster_mimetype    - 'image/png'
    * poster_size        - '320x240'
    * recording_date     - The current time
    * title              - 'Example Video'
    * thumbnail_mimetype - 'image/png'
    * thumnail_size      - '128x128'
    * video_mimetype     - 'video/mp4'
    '''

    orm = None

    try:
        description         = options.get( 'description', 'VIBLIO lets you use the power of video to build strong personal connections.  Keep your memories in motion - with VIBLIO.' )
        filename            = options.get( 'filename', '' )
        geo_address         = options.get( 'geo_address', '1561-1599 Middlefield Road, Palo Alto, CA 94301, USA' )
        geo_city            = options.get( 'geo_city', 'Palo Alto' )
        lat                 = options.get( 'lat', 37.442174 )
        lng                 = options.get( 'lat', -122.143199 )
        poster_mimetype     = options.get( 'poster_mimetype', 'image/png' )
        poster_size         = options.get( 'poster_size', '320x240' )
        recording_date      = options.get( 'recording_date', datetime.datetime.now() )
        title               = options.get( 'title', 'Example Video' )
        thumbnail_mimetype  = options.get( 'thumbnail_mimetype', 'image/png' )
        thumbnail_size      = options.get( 'thumbnail_size', '128x128' )
        video_mimetype      = options.get( 'video_mimetype', 'video/mp4' )

        poster_x   , poster_y    = poster_size.split( 'x' )
        thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )

        media_uuid = str( uuid.uuid4() )

        log.info( json.dumps( {'user_uuid' : user_uuid,
                               'media_uuid' : media_uuid,
                               'message' : "Creating welcome video %s for user %s." % ( media_uuid, user_uuid ) } ) )

        # Copy video file to S3 location for this user.
        video_uri = '%s/%s_output.%s' % ( media_uuid, media_uuid, video_file['format'] )
        poster_uri = '%s/%s_poster.%s' % ( media_uuid, media_uuid, poster_file['format'] )
        if thumbnail_file is not None:
            thumbnail_uri = '%s/%s_thumbnail.%s' % ( media_uuid, media_uuid, thumbnail_file['format'] )

        if poster_animated is not None:
            poster_animated_uri = '%s/%s_poster_animated.%s' % ( media_uuid, media_uuid, poster_animated['format'] )

        vib.utils.s3.copy_s3_file( video_file['s3_bucket'], video_file['s3_key'], config.bucket_name, video_uri )
        vib.utils.s3.copy_s3_file( poster_file['s3_bucket'], poster_file['s3_key'], config.bucket_name, poster_uri )

        if thumbnail_file is not None:
            vib.utils.s3.copy_s3_file( thumbnail_file['s3_bucket'], thumbnail_file['s3_key'], config.bucket_name, thumbnail_uri )

        if poster_animated is not None:
            vib.utils.s3.copy_s3_file( poster_animated['s3_bucket'], poster_animated['s3_key'], config.bucket_name, poster_animated_uri )

        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

        media = Media( 
            uuid        = media_uuid,
            media_type  = 'original',
            filename    = filename,
            title       = title,
            view_count  = 0,
            description = description,
            geo_address = geo_address,
            geo_city    = geo_city,
            lat         = lat,
            lng         = lng,
            recording_date = recording_date,
            status      = 'complete',
            is_viblio_created = True
            )

        user.media.append( media )
        
        video_uuid = str( uuid.uuid4() )
        video_asset = MediaAssets( 
            uuid         = video_uuid,
            asset_type   = 'main',
            mimetype     = video_mimetype,
            bytes        = video_file['bytes'],
            uri          = video_uri,
            location     = 'us',
            view_count   = 0 )
        media.assets.append( video_asset )

        if thumbnail_file is not None:
            thumbnail_uuid = str( uuid.uuid4() )
            thumbnail_asset = MediaAssets( uuid       = thumbnail_uuid,
                                           asset_type = 'thumbnail',
                                           mimetype   = thumbnail_mimetype,
                                           bytes      = thumbnail_file['bytes'],
                                           width      = int( thumbnail_x ), 
                                           height     = int( thumbnail_y ),
                                           uri        = thumbnail_uri,
                                           location   = 'us',
                                           view_count = 0 )
            media.assets.append( thumbnail_asset )

        poster_uuid = str( uuid.uuid4() )
        poster_asset = MediaAssets( uuid       = poster_uuid,
                                    asset_type = 'poster',
                                    mimetype   = poster_mimetype,
                                    bytes      = poster_file['bytes'],
                                    width      = int( poster_x ), 
                                    height     = int( poster_y ),
                                    uri        = poster_uri,
                                    location   = 'us',
                                    view_count = 0 )
        media.assets.append( poster_asset )

        if poster_animated is not None:
            poster_animated_uuid = str( uuid.uuid4() )
            poster_animated_asset = MediaAssets( uuid       = poster_animated_uuid,
                                                 asset_type = 'poster_animated',
                                                 mimetype   = 'image/' + poster_animated['format'],
                                                 bytes      = poster_animated['bytes'],
                                                 width      = int( poster_x ), # Not a typo.
                                                 height     = int( poster_y ), # Not a typo.
                                                 uri        = poster_animated_uri,
                                                 location   = 'us',
                                                 view_count = 0 )
            media.assets.append( poster_animated_asset )

        for idx, face in enumerate( face_files ):
            contact_name        = face.get( 'contact_name', 'VIBLIO Feedback' )
            contact_email       = face.get( 'contact_email', 'feedback@viblio.com' )

            face_mimetype       = face.get( 'face_mimetype', 'image/png' )
            face_size           = face.get( 'face_size', '128x128' )
            face_x,      face_y      = face_size.split( 'x' )
            face_uri = '%s/%s_face_0_%s.%s' % ( media_uuid, media_uuid, idx, face['format'] )
            vib.utils.s3.copy_s3_file( face['s3_bucket'], face['s3_key'], config.bucket_name, face_uri )

            contact = Contacts(
                uuid          = str( uuid.uuid4() ),
                user_id       = user.id,
                # We decided not to have these faces associated with names for new users.
                #contact_name  = contact_name,
                #contact_email = contact_email,
                picture_uri   = face_uri
                )

            orm.add( contact )

            face_uuid = str( uuid.uuid4() )
            face_asset = MediaAssets( uuid       = face_uuid,
                                      asset_type = 'face',
                                      mimetype   = face_mimetype,
                                      bytes      = face['bytes'],
                                      width      = int( face_x ), 
                                      height     = int( face_y ),
                                      uri        = face_uri,
                                      location   = 'us',
                                      view_count = 0 )
            media.assets.append( face_asset )

            media_asset_feature = MediaAssetFeatures(
                feature_type = 'face',
                recognition_result = 'new_face'
                )
                
            face_asset.media_asset_features.append( media_asset_feature )
            contact.media_asset_features.append( media_asset_feature )

        for idx, image in enumerate( image_files ):
            image_mimetype       = image.get( 'image_mimetype', 'image/png' )
            image_size           = image.get( 'image_size', '1280x720' )
            image_x,      image_y      = image_size.split( 'x' )
            image_uri = '%s/%s_image_0_%s.%s' % ( media_uuid, media_uuid, idx, image['format'] )
            vib.utils.s3.copy_s3_file( image['s3_bucket'], image['s3_key'], config.bucket_name, image_uri )

            image_uuid = str( uuid.uuid4() )
            image_asset = MediaAssets( uuid       = image_uuid,
                                       asset_type = 'image',
                                       mimetype   = image_mimetype,
                                       bytes      = image['bytes'],
                                       width      = int( image_x ), 
                                       height     = int( image_y ),
                                       uri        = image_uri,
                                       timecode = image.get( 'image_timecode', 0 ),
                                       face_score = image.get( 'image_face_score', 0 ),
                                       blur_score = image.get( 'image_blur_score', 0 ),
                                       location   = 'us',
                                       view_count = 0 )
            media.assets.append( image_asset )

        orm.commit()
    
        # Determine if we need to create and or add to the special
        # video tutorial album.
        viblio_tutorial_album = orm.query( Media ).filter( and_( Media.user_id == media.user_id, Media.is_viblio_created == True, Media.title == config.viblio_tutorial_album_name ) )[:]
            
        if len( viblio_tutorial_album ) == 0:
            viblio_tutorial_album = Media( user_id = media.user_id,
                                           uuid = str( uuid.uuid4() ),
                                           media_type = 'original',
                                           is_album = True,
                                           title = config.viblio_tutorial_album_name,
                                           is_viblio_created = True )
            orm.add( viblio_tutorial_album )
                
            media_album_row = MediaAlbums()
            orm.add( media_album_row )
            media.media_albums_media.append( media_album_row )
            viblio_tutorial_album.media_albums.append( media_album_row )

            album_poster = MediaAssets( user_id = media.user_id,
                                        uuid = str( uuid.uuid4() ),
                                        asset_type = 'poster',
                                        mimetype = poster_asset.mimetype,
                                        location = poster_asset.location,
                                        uri = poster_asset.uri, 
                                        width = poster_asset.width,
                                        height = poster_asset.height )
            viblio_tutorial_album.assets.append( album_poster )

        elif len( viblio_tutorial_album ) == 1:
            media_album_row = MediaAlbums()
            orm.add( media_album_row )
            media.media_albums_media.append( media_album_row )
            viblio_tutorial_album[0].media_albums.append( media_album_row )

            album_posters = orm.query( MediaAssets ).filter( and_( MediaAssets.media_id == media.id, MediaAssets.asset_type == 'poster' ) ).all()
            if len( album_posters ) == 0:
                album_poster = MediaAssets( user_id = media.user_id,
                                            uuid = str( uuid.uuid4() ),
                                            asset_type = 'poster',
                                            mimetype = poster_asset.mimetype,
                                            location = poster_asset.location,
                                            uri = poster_asset.uri, 
                                            width = poster_asset.width,
                                            height = poster_asset.height )
                viblio_tutorial_album.assets.append( album_poster )

        else:
            raise Exception( "ERROR: Found multiple %s albums for user: %s " % ( config.viblio_tutorial_album_name, media.user_id ) )

        orm.commit()

        # Try to send a notification to CAT that we created these videos.
        try:
            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Notifying Cat server of video creation at %s' %  config.viblio_server_url } ) )
            site_token = hmac.new( config.site_secret, user_uuid ).hexdigest()
            res = requests.get( config.viblio_server_url, params={ 'uid': user_uuid, 'mid': media_uuid, 'site-token': site_token } )
            body = ''
            if hasattr( res, 'text' ):
                body = res.text
            elif hasattr( res, 'content' ):
                body = str( res.content )
            else:
                print 'Error: Cannot find body in response!'
            jdata = json.loads( body )

            if 'error' in jdata:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "Error notifying CAT, message was: %s" % jdata['message'] } ) )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "Error sending notification to CAT for user, error was: %s" % ( e ) } ) )

    except Exception as e:
        if orm != None:
            orm.rollback()
        log.error( json.dumps( { 'user_uuid' : user_uuid,
                                 'message' : "Exception was: %s" % e } ) )
        raise

def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

sqs = __get_sqs().get_queue( config.new_account_creation_queue )
sqs.set_message_class( RawMessage )

def run():
    try:
        message = None
        message = sqs.read( wait_time_seconds = 20 )
        
        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()
        
        try:
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body was %s: " % ( body ) } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % ( e ) } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % ( options ) } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %e" % ( e ) } ) )
        
        user_uuid = options.get( 'user_uuid', None )
        action    = options.get( 'action', '' )

        if action == 'welcome_video' and user_uuid != None:
            # Process message
            log.info( json.dumps( { 'message' : "Starting greet_new_users, message body was %s: " % body } ) )

            # Need to delete the message here or it can get processed multiple times.
            sqs.delete_message( message )


            '''
            welcome_video_for_user(
                title = 'Example Video 1',
                user_uuid = user_uuid,
                video_file = { 
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-001/video.mp4', 
                    'bytes'     : 3695399,
                    'format'    : 'mp4'
                    },
                thumbnail_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-001/thumbnail.png',
                    'bytes'     : 21361,
                    'format'    : 'png'
                    },
                poster_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-001/poster.png',
                    'bytes'     : 174831,
                    'format'    : 'png'
                    },
                face_files = [ {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-001/face.png',
                        'bytes'     : 13153,
                        'format'    : 'png',
                        'face_size' : '800x800'
                        } ]
                )
                '''

            welcome_video_for_user(
                title = 'Getting Started with VIBLIO',
                description = 'This is a very short tutorial to help you get started with your new VIBLIO account',
                user_uuid = user_uuid,
                video_file = { 
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-004/video.mp4', 
                    'bytes'     : 17197235,
                    'format'    : 'mp4'
                    },
                poster_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-004/poster.png',
                    'bytes'     : 53510,
                    'format'    : 'png'
                    },
                poster_animated = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-004/poster_animated.gif',
                    'bytes'     : 301740,
                    'format'    : 'gif'
                    },
                image_files = [ 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-01.jpg',
                        'bytes'     : 99453,
                        'format'    : 'jpg',
                        'image_timecode' : 10,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-02.jpg',
                        'bytes'     : 149377,
                        'format'    : 'jpg',
                        'image_timecode' : 50,
                        'face_score' : 1,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-03.jpg',
                        'bytes'     : 125868,
                        'format'    : 'jpg',
                        'image_timecode' : 120,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-04.jpg',
                        'bytes'     : 93256,
                        'format'    : 'jpg',
                        'image_timecode' : 160,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-05.jpg',
                        'bytes'     : 37900,
                        'format'    : 'jpg',
                        'image_timecode' : 170,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-06.jpg',
                        'bytes'     : 75025,
                        'format'    : 'jpg',
                        'image_timecode' : 180,
                        'face_score' : 1,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-004/image-07.jpg',
                        'bytes'     : 107600,
                        'format'    : 'jpg',
                        'image_timecode' : 190,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    ]
                )

            welcome_video_for_user(
                title = 'Welcome to VIBLIO',
                description = 'Your INTELLIGENT Video Library',
                user_uuid = user_uuid,
                video_file = { 
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-003/video.mp4', 
                    'bytes'     : 15820189,
                    'format'    : 'mp4'
                    },
                thumbnail_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-003/thumbnail.png',
                    'bytes'     : 3571,
                    'format'    : 'png'
                    },
                poster_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-003/poster.png',
                    'bytes'     : 10148,
                    'format'    : 'png'
                    },
                face_files = [ 
                    {
                        'contact_name' : 'Mona',
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-003/face.png',
                        'bytes'     : 8954,
                        'format'    : 'png',
                        'face_size' : '128x128'
                        }, 
                    ],
                image_files = [ 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-003/image-01.jpg',
                        'bytes'     : 43561,
                        'format'    : 'jpg',
                        'image_timecode' : 30,
                        'face_score' : 1,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-003/image-02.jpg',
                        'bytes'     : 83545,
                        'format'    : 'jpg',
                        'image_timecode' : 70,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    {
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-003/image-03.jpg',
                        'bytes'     : 115395,
                        'format'    : 'jpg',
                        'image_timecode' : 80,
                        'face_score' : 0,
                        'face_size' : '1280x720'
                        }, 
                    ]
                )

            '''
            welcome_video_for_user(
                title = 'Example Video 2',
                description = 'Rediscover your favorite family videos with VIBLIO and watch what matters. Reserve your spot now for the revolutionary video-storing and sharing platform at https://viblio.com/signup/',
                user_uuid = user_uuid,
                video_file = { 
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-002/video.mp4', 
                    'bytes'     : 6538113,
                    'format'    : 'mp4'
                    },
                thumbnail_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-002/thumbnail.png',
                    'bytes'     : 19632,
                    'format'    : 'png'
                    },
                poster_file = {
                    's3_bucket' : 'viblio-external',
                    's3_key'    : 'media/video-002/poster.png',
                    'bytes'     : 154269,
                    'format'    : 'png'
                    },
                face_files = [ 
                    {
                        'contact_name' : 'Isabella',
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-002/face_00.png',
                        'bytes'     : 3828,
                        'format'    : 'png',
                        'face_size' : '168x168'
                        }, 
                    {
                        'contact_name' : 'Emily',
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-002/face_01.png',
                        'bytes'     : 3731,
                        'format'    : 'png',
                        'face_size' : '147x147'
                        },
                    {
                        'contact_name' : 'James',
                        's3_bucket' : 'viblio-external',
                        's3_key'    : 'media/video-002/face_02.png',
                        'bytes'     : 4491,
                        'format'    : 'png',
                        'face_size' : '148x148'
                        } 
                    ]
                )
                '''

            return True
        else:
            # This message is not for us or is malformed - someone
            # else can handle it.
            return True
            
        return True

    except Exception as e:
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise
    finally:
        if message != None and options != None and options.get( 'action', '' ) == 'welcome_video':
            # Even if something went wrong, make sure we delete the
            # message so we don't end up stuck in an infinite loop
            # trying to process this message.
            sqs.delete_message( message )

