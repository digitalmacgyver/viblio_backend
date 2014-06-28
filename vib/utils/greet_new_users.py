#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
import datetime
import json
import logging
from logging import handlers
import os
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

def welcome_video_for_user( user_uuid, video_file, poster_file, thumbnail_file, face_files, **options ):
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
    * contact_name       - 'Viblio'

    Optional keyword arguments exist with the following defaults: 
 
    * description        - 'Viblio lets you use the power of video to build strong personal connections.  Keep your memories in motion - with Viblio.'
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
        description         = options.get( 'description', 'Viblio lets you use the power of video to build strong personal connections.  Keep your memories in motion - with Viblio.' )
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

        log.info( json.dumps( {
                    'user_uuid' : user_uuid,
                    'media_uuid' : media_uuid,
                    'message' : "Creating welcome video %s for user %s." % ( media_uuid, user_uuid )
                    } ) )

        # Copy video file to S3 location for this user.
        video_uri = '%s/%s_output.%s' % ( media_uuid, media_uuid, video_file['format'] )
        poster_uri = '%s/%s_poster.%s' % ( media_uuid, media_uuid, poster_file['format'] )
        thumbnail_uri = '%s/%s_thumbnail.%s' % ( media_uuid, media_uuid, thumbnail_file['format'] )

        vib.utils.s3.copy_s3_file( video_file['s3_bucket'], video_file['s3_key'], config.bucket_name, video_uri )
        vib.utils.s3.copy_s3_file( poster_file['s3_bucket'], poster_file['s3_key'], config.bucket_name, poster_uri )
        vib.utils.s3.copy_s3_file( thumbnail_file['s3_bucket'], thumbnail_file['s3_key'], config.bucket_name, thumbnail_uri )

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
            status      = 'complete'
            )

        user.media.append( media )

        # Check of this user has the special album:
        all_videos_album = None
        all_videos = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.is_viblio_created == True, Media.title == 'My Videos' ) )[:]

        if len( all_videos ) == 0:
            all_videos_album = Media( user_id = user.id,
                                     uuid = str( uuid.uuid4() ),
                                     media_type = 'original',
                                     is_album = True,
                                     display_album = True,
                                     title = 'My Videos',
                                     is_viblio_created = True )
            orm.add( all_video_album )
        elif len( all_videos ) == 1:
            all_videos_album = all_videos[0]
        else:
            raise Exception( "ERROR: Found multiple 'My Videos' albums for user: %s " % ( user.id ) )
                
        media_album_row = MediaAlbums()
        orm.add( media_album_row )
        media.media_albums_media.append( media_album_row )
        all_videos_album.media_albums.append( media_album_row )

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

        for idx, face in enumerate( face_files ):
            contact_name        = face.get( 'contact_name', 'Viblio' )

            face_mimetype       = face.get( 'face_mimetype', 'image/png' )
            face_size           = face.get( 'face_size', '128x128' )
            face_x,      face_y      = face_size.split( 'x' )
            face_uri = '%s/%s_face_0_%s.%s' % ( media_uuid, media_uuid, idx, face['format'] )
            vib.utils.s3.copy_s3_file( face['s3_bucket'], face['s3_key'], config.bucket_name, face_uri )

            # First off, get or create a contact_group for this user.
            contact_groups = user.groups.filter( Groups.group_type == 'contact' )[:]
            contact_group = None
            if len( contact_groups ) == 0:
                # We need to create a contact group for this user.
                contact_group = ContactGroups( uuid = str( uuid.uuid4() ),
                                               group_type = 'contact',
                                               group_name = 'Contacts' )
                user.append( contact_group )
            elif len( contact_groups ) > 1:
                log.error( json.dumps( { 'user_uuid' : user.uuid,
                                         'message' : "Found multiple contact groups for single user.id %s - there should be only one, mapping to the oldest one: %s" % ( user_id, contact_groups[0].id ) } ) )
                contact_group = contact_groups[0]
            else:
                contact_group = contact_groups[0]

            contact_user = Users( uuid        = str( uuid.uuid4() ),
                                  displayname = contact_name,
                                  user_type   = 'contact' )
            orm.add( contact_user )

            contact_user_group = UserGroups( uuid        = str( uuid.uuid4() ),
                                             member_name = contact_name,
                                             member_role = 'contact',
                                             picture_uri = face_uri )
            contact_user.user_groups.append( contact_user_group )
            contact_group.user_groups.append( contact_user_group )

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
                feature_type = 'face'
                )
                
            face_asset.media_asset_features.append( media_asset_feature )
            contact_user.media_asset_features.append( media_asset_feature )
        
        orm.commit()
    
    except Exception as e:
        if orm != None:
            orm.rollback()
        log.error( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
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
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body was %s: " % body } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % e } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % options } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %e" % e } ) )
        
        user_uuid = options.get( 'user_uuid', None )
        action    = options.get( 'action', '' )

        if action == 'welcome_video' and user_uuid != None:
            # Process message
            log.info( json.dumps( { 'message' : "Starting greet_new_users, message body was %s: " % body } ) )

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
                title = 'Welcome to Viblio',
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
                    ]
                )

            welcome_video_for_user(
                title = 'Example Video 2',
                description = 'Rediscover your favorite family videos with Viblio and watch what matters. Reserve your spot now for the revolutionary video-storing and sharing platform at https://viblio.com/signup/',
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
            
            sqs.delete_message( message )
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

