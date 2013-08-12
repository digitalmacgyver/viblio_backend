import datetime
import logging
import os
import random
import sys
import uuid

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'create_test_data' ).config()

logging.basicConfig( filename = config['logfile'], level = config.loglevel )

log = logging.getLogger( __name__ )

def _get_conn( engine ):
    try:
        if not hasattr( _get_meta, 'conn' ):
            log.info( "Creating a database connection." )
            _get_conn.conn = engine.connect()
        return _get_conn.conn
    except Exception, e:
        log.critical( "Failed to get database connection. Error: %s" % e )
        raise

def _get_meta( engine ):
    try:
        log.info( "Getting SQLAlchemy data structures from the database." )
        if not hasattr( _get_meta, 'meta' ):
            _get_meta.meta = MetaData()
            _get_meta.meta.reflect( bind = engine )
        return _get_meta.meta
    except Exception, e:
        log.critical( "Failed to get SQLAlchemy metadata. Error: %s" % e )
        raise

def get_user_for_uuid( engine, user_uuid ):
    try:
        conn = _get_conn( engine )
        meta = _get_meta( engine )
        users = meta.tables['users']
        return conn.execute( select( [users] ).where( users.c.uuid == user_uuid ) ).fetchone()
    except Exception, e:
        log.critical( "Failed to find user id for user uuid %s.  Error: %s" % ( user_uuid, e ) )
        raise

def get_user_id_for_uuid( engine, user_uuid ):
    try:
        if not hasattr( get_user_id_for_uuid, 'id_map' ):
            get_user_id_for_uuid.id_map = {}
        if user_uuid not in get_user_id_for_uuid.id_map:
            get_user_id_for_uuid.id_map[user_uuid] = get_user_for_uuid( engine, user_uuid)['id']
        return get_user_id_for_uuid.id_map[user_uuid]
    except Exception, e:
        log.critical( "Failed to find user id for user uuid %s.  Error: %s" % ( user_uuid, e ) )
        raise

def create_test_contacts( engine, user_id, contact_list ):
    '''Given a user_id and a data structure of contacts, insert the
    contacts for that user_id into the database.  Also, populate the
    contacts data structure with the ids of the inserted contacts.

    contacts = [ { name, email, provider, provider_id, viblio_id }, ... ]'''
    try:
        log.info( "Inserting contacts for user_id %s" % ( user_id ) )
        conn = _get_conn( engine )
        meta = _get_meta( engine )
        contacts = meta.tables['contacts']
        for contact in contact_list:
            log.info( "Adding contact: %s" % ( contact['name'] ) )
            result = conn.execute( contacts.insert(),
                                   id                = None,
                                   user_id           = user_id,
                                   contact_name      = contact['name'],
                                   contact_email     = contact['email'],
                                   contact_viblio_id = contact['viblio_id'],
                                   provider          = contact['provider'],
                                   provider_id       = contact['provider_id'] )
            contact['id'] = result.inserted_primary_key[0]
            log.info( "Inserted contact id is: %s" % ( contact['id'] ) )
    except Exception, e:
        log.critical( "Failed to insert contacts. Error: %s" % ( e ) )
        raise
        
def create_test_videos( engine, user_id, videos, faces, contacts ):
    '''Given an array of video, face, and contact data structures
    populates media, media_assets, media_asset_features with the
    relevant data.'''
    try:
        log.info( "Inserting test videos for user_id %s" % ( user_id ) )
        conn = _get_conn( engine )
        meta = _get_meta( engine )
        media = meta.tables['media']
        media_assets = meta.tables['media_assets']
        media_asset_features = meta.tables['media_asset_features']
        
        for video in videos:
            # Add the media row
            video['uuid'] = str( uuid.uuid4() )
            v_result = conn.execute( media.insert(),
                                     id             = None, # Populated by the database.
                                     user_id        = user_id,
                                     uuid           = video['uuid'],
                                     media_type     = 'original',
                                     title          = 'unit_test_insert',
                                     filename       = video['s3_key'],
                                     description    = 'unit_test_insert',
                                     recording_date = datetime.datetime.now(),
                                     view_count     = 0,
                                     lat            = float( "%.8f" % random.uniform(-180,180) ),
                                     lng            = float( "%.8f" % random.uniform(-180,180) ) )
            video['id'] = v_result.inserted_primary_key[0]

            # Add the main asset row
            # DEBUG - assumes this URI exists in S3 already
            # DEBUG - doesn't set bytes.
            video['main_uuid'] = str( uuid.uuid4() )
            result_id = add_asset( conn=conn, media_assets=media_assets, row=video, 
                                   uuid=video['main_uuid'],
                                   asset_type='main', 
                                   mimetype='video/mp4',
                                   uri=video['uuid']+'/'+video['uuid']+'.mp4',
                                   metadata_uri=video['uuid']+'/'+video['uuid']+'_metadata.json' )
            video['main_id'] = result_id

            # Add the thumbnail row
            # DEBUG - assumes this URI exists in S3 already
            # DEBUG - doesn't set bytes.
            video['thumbnail_uuid'] = str( uuid.uuid4() )
            result_id = add_asset( conn=conn, media_assets=media_assets, row=video, 
                                   uuid=video['thumbnail_uuid'], 
                                   asset_type='thumbnail', 
                                   mimetype='image/jpg',
                                   uri=video['uuid']+'/'+video['uuid']+'_thumbnail.jpg',
                                   metadata_uri=None )
            video['thumbnail_id'] = result_id

            # Add the poster row
            # DEBUG - assumes this URI exists in S3 already
            # DEBUG - doesn't set bytes.
            video['poster_uuid'] = str( uuid.uuid4() )
            result_id = add_asset( conn=conn, media_assets=media_assets, row=video, 
                                   uuid=video['poster_uuid'],
                                   asset_type='poster', 
                                   mimetype='image/jpg',
                                   uri=video['uuid']+'/'+video['uuid']+'_poster.jpg',
                                   metadata_uri=None )
            video['poster_id'] = result_id

            for face_idx in video['face_idx']:
                # Add a face row for each face
                face = faces[face_idx]
                face_uuid = str( uuid.uuid4() )
                face_uri = video['uuid']+'/face-' + face_uuid+'.jpg'
                face_id = add_asset( conn=conn, media_assets=media_assets, row=video, 
                                     uuid=face_uuid,
                                     asset_type='face', 
                                     mimetype='image/jpg',
                                     uri=face_uri,
                                     metadata_uri=None, bytes=face['size'] )

                log.info( 'S3 copy of face from %s to %s' % ( face['s3_key'], face_uri  ) ) 
                bucket = _get_bucket()
                bucket.copy_key( face_uri, config.bucket_name, face['s3_key'] )

                # Add a feature row for each face
                contact_id = None
                if face['contact_idx']:
                    contact_id = contacts[face['contact_idx']]['id']
                add_feature( conn=conn, media_asset_features=media_asset_features,
                             media_asset_id = face_id,
                             feature_type = 'face',
                             coordinates = "{ 'x1':0, 'y1':0, 'x2':"+str( face['width'] )+", 'y2':"+str( face['height'] )+" }",
                             contact_id = contact_id )
                
    except Exception, e:
        log.critical( "Failed to set up test data. Error: %s" % ( e ) )
        raise


def add_feature( conn, media_asset_features, media_asset_id, feature_type, coordinates, contact_id ):
    try:
        log.info( "Inserting feature for asset %s of type %s" % ( media_asset_id, feature_type ) )
        result = conn.execute( media_asset_features.insert(),
                      id = None,
                      media_asset_id = media_asset_id,
                      feature_type = feature_type,
                      coordinates = coordinates,
                      contact_id = contact_id )
        log.info( "Inserted feature has id: %s" % ( result.inserted_primary_key[0] ) )
    except Exception, e:
        log.critical( "Failed to insert feature. Error: %s" % ( e ) ) 
        raise

def add_asset( conn, media_assets, row, uuid, asset_type, mimetype, uri, metadata_uri, bytes=None ):
    try:
        log.info( "Inserting asset for %s of type %s" % ( uri, asset_type ) )
        result = conn.execute( media_assets.insert(),
                               id             = None, # Populated by the database.
                               media_id       = row['id'],
                               uuid           = uuid,
                               asset_type     = asset_type,
                               mimetype       = mimetype,
                               uri            = uri,
                               location       = 'us',
                               metadata_uri   = metadata_uri,
                               view_count     = 0
                               )
        log.info( "Inserted asset has id %s" % ( result.inserted_primary_key[0] ) )
        return result.inserted_primary_key[0]
    except Exception, e:
        log.critical( "Failed to insert asset. Error: %s" % ( e ) )
        raise



def _get_bucket():
    try:
        if not hasattr( _get_bucket, "bucket" ):
            _get_bucket.bucket = None
        if _get_bucket.bucket == None:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            _get_bucket.bucket = s3.get_bucket(config.bucket_name)
            bucket_contents = Key(_get_bucket.bucket)
        return _get_bucket.bucket
    except Exception, e:
        log.critical( 'Failed to obtain s3 bucket: %s' % str(e) )
        raise

def _check_file( file_name, mode=os.R_OK ):
    try:
        if os.access( file_name, mode ):
            log.info( "Verified access to file: '%s' With mode: '%s'" % ( file_name, str( mode ) ) )
            return True
        else:
            log.warn( "Failed to access file: '%s' With mode: '%s'" % ( file_name, str( mode ) ) )
            return False
    except Exception, e:
        log.critical( "Failed to access file: '%s' With mode: '%s' Error was: %s" % ( file_name, str( mode ), str( e ) ) )
        raise

def upload_file_to_s3( file_name, s3_key ):
    try:
        if ( _check_file( file_name ) ):
            log.info( 'Uploading file: %s to s3: %s' % ( file_name, s3_key ) )
            bucket = _get_bucket()
            k = Key( bucket )
            k.key = s3_key
            k.set_contents_from_filename( file_name )
    except Exception, e:
        log.critical( "Failed to upload file: '%s' To s3 key: '%s' Error was: %s" % ( file_name, s3_key, str( e ) ) )
        raise

def download_file_from_s3( file_name, s3_key ):
    try:
        log.info( 'Downloading s3 file %s to: %s' % ( s3_key, file_name ) )
        bucket = _get_bucket()
        k = Key( bucket )
        k.key = s3_key
        k.get_contents_to_filename( file_name )
    except Exception, e:
        log.critical( "Failed to download to file: '%s' From s3 key: '%s' Error was: %s" % ( file_name, s3_key, str( e ) ) )
        raise
        
