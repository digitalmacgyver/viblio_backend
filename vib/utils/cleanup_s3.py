#!/usr/bin/env python

import logging
from optparse import OptionParser
import re
from sqlalchemy import and_, exists
import sys

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.cleanup_s3' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'cleanup_s3: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )



def cleanup_s3( delete = False ):
    orm = vib.db.orm.get_session()
    
    if config.bucket_name != 'viblio-uploaded-files':
        raise Exception( "DO NOT RUN THIS IN PROD!" )
        sys.exit( 1 )

    bucket = s3._get_bucket( config.bucket_name )
    
    total_size = 0
    total_count = 0

    deleted_size = 0
    deleted_count = 0

    valid_size = 0
    valid_count = 0

    media_uuid_metadata = {}

    i = 0
    for thing in bucket.list():
        total_size += thing.size
        total_count += 1

        m = re.match( r'^([^/]+)', thing.key )
        media_uuid = None
        if m.groups():
            media_uuid = m.groups()[0]

        if media_uuid is None:
            print "UNEXPECTED URI FORMAT: %s - SKIPPING." % ( thing.key )
            continue

        if media_uuid == 'test_data':
            continue

        valid_size += thing.size
        valid_count += 1

        if thing.key in [ "%s/%s.json" % ( media_uuid, media_uuid ), # Upload.json
                          "%s/%s_metadata.json" % ( media_uuid, media_uuid ), # Upload metadata
                          "%s/%s_recognition_input.json" % ( media_uuid, media_uuid ),
                          "%s/%s_faces.json" % ( media_uuid, media_uuid ) ]:
            # We take no action here on metadata files.
            if media_uuid in media_uuid_metadata:
                media_uuid_metadata[media_uuid].append( thing.key )
            else:
                media_uuid_metadata[media_uuid] = [ thing.key ]
            continue

        if orm.query( exists().where( MediaAssets.uri == thing.key ) ).scalar():
            pass
            #print "URI exists in database.", thing.key
        else:
            print "URI does not exist in database, deleting: ", thing.key
            if delete:
                s3.delete_s3_file( config.bucket_name, thing.key )
            deleted_size += thing.size
            deleted_count += 1

        #print i
        i += 1
        if i % 1000 == 0:
            print ".",

    print "Total count: %d - %d = %d" % ( total_count, deleted_count, total_count - deleted_count )
    print "Total size : %f - %f = %f" % ( float( total_size )/1024/1024/1024, float( deleted_size) /1024/1024/1024, float(total_size - deleted_size)/1024/1024/1024 )
    print "Valid count: %d size: %f" % ( valid_count, float( valid_size)/1024/1024/1024 )

    cleanup_db( media_uuid_metadata, delete )

def cleanup_db( s3_media_metadata, delete = False ):
    orm = vib.db.orm.get_session()

    db_uris = {}
    db_uuids = {}
    
    i = 0
    for asset in orm.query( MediaAssets ).filter( MediaAssets.asset_type.in_( [ 'image', 'fb_face', 'main', 'main_sd', 'poster', 'poster_animated', 'poster_original', 'thumbnail', 'thumbnail_animated', 'face' ] ) ):
        i += 1
        if i % 100 == 0:
            print "-",
        if asset.uri is not None:
            db_uris[asset.uri] = asset

            m = re.match( r'^([^/])+', asset.uri )
            if m.groups():
                db_uuids[ m.groups()[0] ] = True
        else:
            # Assets without URIs are people identified to be in a video for which we have no photo.
            if asset.asset_type != 'face':
                print "WARNING: asset id: %d had no URI but is not of type face." % ( asset.id )

    deleted_media_ids = {}

    i = 0
    for uri, asset in db_uris.items():
        i += 1
        if i % 100 == 0:
            print "+",
        # If this media is already scheduled for possible deletion, just move on.

        if asset.media_id in deleted_media_ids:
            continue
        else:
            media = asset.media

            if media.media_type != 'original':
                # We are only handling media of type original.
                continue

            if not s3.check_exists( config.bucket_name, uri ):
                print "DB URI: %s is not in s3" % ( uri ),
                
                # We have a few cases here:
                # 1. Asset type is not main or poster, in this case delete the asset.
                # 2. Media is an album and asset is a poster, in this case add the default poster.
                # 3. Asset type is main or poster, in this case delete the media.
                if asset.asset_type not in [ 'main', 'poster' ]:
                    print "deleting asset %d of type %s" % ( asset.id, asset.asset_type )
                    if delete:
                        orm.delete( asset )
                        orm.commit()
                else:
                    if media.is_album and asset.asset_type == 'poster':
                        print " - copying default album poster to this URI."
                        poster_uri = asset.uri
                        s3.copy_s3_file( 'viblio-external', 'media/default-images/DEFAULT-poster.png', config.bucket_name, poster_uri )
                        asset.bytes = s3.check_exists( config.bucket_name, poster_uri ).size
                        asset.width = 288
                        asset.height = 216
                        orm.commit()
                    else:
                        # Just delete the entire media.
                        deleted_media_ids[media.id] = True
                        if delete:
                            orm.delete( media )
                            orm.commit()


    for uuid, uris in s3_media_metadata.items():
        if uuid not in db_uuids:
            for uri in uris:
                print "DB UUID: %s does not exist, deleting metadata %s from S3" % ( uuid, uri )
                if delete:
                    s3.delete_file( config.bucket_name, uri )
                
    no_main_videos = orm.query( Media ).filter( and_( Media.media_type == 'original', Media.is_album != 1, Media.status.in_( [ 'visible', 'complete' ] ), ~Media.assets.any( MediaAssets.asset_type == 'main' ) ) )

    for no_main in no_main_videos:
        print "No video for:", no_main.uuid, "deleting."
        if delete:
            orm.delete( no_main )
            orm.commit()

delete = True

cleanup_s3( delete )


