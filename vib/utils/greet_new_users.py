#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
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

format_string = 'fb: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )


# Logic:
# Review test user create to see how to do some of this.
# Copy from stored S3 to desired S3
# Store media, media_asset in DB
# Set title
# Set description
# Set date
# Set location

def welcome_video_for_user( user_uuid, video_file, poster_file, thumbnail_file, **options ):
    '''Adds the video, thumbnail, and poster for the user_uuid.
    
    Each of the _file arguments is a dictionary with:
    * s3_bucket
    * s3_key
    * bytes
    * format
    keys

    Optional keyword arguments exist with the following defaults: 
 
    * description        - 'Safe, secure video sharing'
    * filename           - ''
    * lat                - None
    * lng                - None
    * poster_mimetype    - 'image/jpg'
    * poster_size        - '320x180'
    * recording_date     - The current time
    * title              - 'Welcome to Viblio'
    * thumbnail_mimetype - 'image/jpg'
    * thumnail_size      - '128x128'
    * video_mimetype     - 'video/mp4'
    '''

    orm = None

    try:
        description         = options.get( 'description', 'Safe, secure video sharing' )
        filename            = options.get( 'filename', '' )
        lat                 = options.get( 'lat', None )
        lng                 = options.get( 'lat', None )
        poster_mimetype     = options.get( 'poster_mimetype', 'image/png' )
        poster_size         = options.get( 'poster_size', '320x180' )
        recording_date      = options.get( 'recording_date', datetime.datetime.now() )
        title               = options.get( 'title', 'Welcome to Viblio' )
        thumbnail_mimetype  = options.get( 'thumbnail_mimetype', 'image/png' )
        thumbnail_size      = options.get( 'thumbnail_size', '128x128' )
        video_mimetype      = options.get( 'video_mimetype', 'video/mp4' )

        poster_x   , poster_y    = poster_size.split( 'x' )
        thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )

        media_uuid = str( uuid.uuid4() )

        # Copy video file to S3 location for this user.
        video_uri = '%s/%s_output.%s' % ( media_uuid, media_uuid, video_file['format'] )
        poster_uri = '%s/%s_poster.%s' % ( media_uuid, media_uuid, poster_file['format'] )
        thumbnail_uri = '%s/%s_thumbnail.%s' % ( media_uuid, media_uuid, thumbnail_file['format'] )

        vib.utils.s3.copy_s3_file( video_file['s3_bucket'], video_file['s3_key'], config.bucket_name, video_uri )
        vib.utils.s3.copy_s3_file( poster_file['s3_bucket'], poster_file['s3_key'], config.bucket_name, poster_uri )
        vib.utils.s3.copy_s3_file( thumbnail_file['s3_bucket'], thumbnail_file['s3_key'], config.bucket_name, thumbnail_uri )

        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

        #contact = Contacts(
        #    uuid         = str( uuid.uuid4() ),
        #    user_id      = user.id,
        #    contact_name = friend['name'],
        #    provider     = 'facebook',
        #    provider_id  = friend['facebook_id'],
        #    picture_uri  = s3_key
        #    )

        #orm.add( contact )
        
        media = Media( 
            uuid        = media_uuid,
            media_type  = 'original',
            filename    = filename,
            title       = title,
            view_count  = 0,
            description = description,
            lat         = lat,
            lng         = lng,
            recording_date = recording_date,
            status      = 'TranscodeComplete'
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

                #media_asset = MediaAssets(
                #    uuid       = str( uuid.uuid4() ),
                #    asset_type = 'fb_face',
                #    mimetype   = 'image/png',
                #    bytes      = os.path.getsize( friend['file'] ),
                #    uri        = s3_key,
                #    location   = 'us'
                #    )
                #media.assets.append( media_asset )

                #media_asset_feature = MediaAssetFeatures(
                #    feature_type = 'fb_face',
                #    )
                
                #media_asset.media_asset_features.append( media_asset_feature )
                #contact.media_asset_features.append( media_asset_feature )
                
        #contact = Contacts(
        #    uuid         = str( uuid.uuid4() ),
        #    user_id      = user.id,
        #    contact_name = friend['name'],
        #    provider     = 'facebook',
        #    provider_id  = friend['id']
        #    )

        #orm.add( contact )
        
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

def run():
    try:
        message = None
        message = sqs.read( wait_time_seconds = 20 )
        
        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()
        
        try:
            log.debug( json.dumps( {
                        'message' : "Starting greet_new_users, message body was %s: " % body
                        } ) )
        except Exception as e:
            log.debug( json.dumps( {
                        'message' : "Error converting body to string, error was: %s" % e
                        } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( {
                        'message' : "Options are %s: " % options
                        } ) )
        except Exception as e:
            log.debug( json.dumps( {
                        'message' : "Error converting options to string: %e" % e
                        } ) )
        
        user_uuid = options.get( 'user_uuid', None )
        action    = options.get( 'action', '' )

        if action == 'welcome_video' and user_uuid != None:
            # Process message
            welcome_video_for_user(
                user_uuid = user_uuid,
                video_file = { 
                    's3_bucket' : 'viblio-uploaded-files',
                    's3_key'    : 'test_data/videos/test-01.mp4', 
                    'bytes'     : 48511420,
                    'format'    : 'mp4'
                    },
                thumbnail_file = {
                    's3_bucket' : 'viblio-uploaded-files',
                    's3_key'    : 'test_data/videos/test-01_thumbnail.jpg',
                    'bytes'     : 2025,
                    'format'    : 'jpg'
                    },
                poster_file = {
                    's3_bucket' : 'viblio-uploaded-files',
                    's3_key'    : 'test_data/videos/test-01_poster.jpg',
                    'bytes'     : 4353,
                    'format'    : 'jpg'
                    },
                video_mimetype = 'video/mp4',
                thumbnail_mimetype = 'image/jpg',
                poster_mimetype = 'image/jpg',
                )
            sqs.delete_message( message )
            return True
        else:
            # This message is not for us or is malformed - someone
            # else can handle it.
            return True
            
        return True

    except Exception as e:
        log.error( json.dumps( {
                    'message' : "Exception was: %s" % e
                    } ) )
        raise
    finally:
        if message != None and options != None and options.get( 'action', '' ) == 'welcome_video':
            # Even if something went wrong, make sure we delete the
            # message so we don't end up stuck in an infinite loop
            # trying to process this message.
            sqs.delete_message( message )

