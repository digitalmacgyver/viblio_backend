import datetime
import logging
import os
import random
import sys
import uuid
from sqlalchemy import *

import boto
from boto.s3.key import Key

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

engine = create_engine( 'mysql+mysqldb://'
                        +config.db_user+':'+config.db_pass
                        +config.db_conn
                        +config.db_name )

log = logging.getLogger( __name__ )

def get_conn():
    try:
        if not hasattr( get_meta, 'conn' ):
            log.info( "Creating a database connection." )
            get_conn.conn = engine.connect()
        return get_conn.conn
    except Exception, e:
        log.critical( "Failed to get database connection. Error: %s" % e )
        raise

def get_meta():
    try:
        log.info( "Getting SQLAlchemy data structures from the database." )
        if not hasattr( get_meta, 'meta' ):
            get_meta.meta = MetaData()
            get_meta.meta.reflect( bind = engine )
        return get_meta.meta
    except Exception, e:
        log.critical( "Failed to get SQLAlchemy metadata. Error: %s" % e )
        raise

def get_bucket():
    try:
        if not hasattr( get_bucket, "bucket" ):
            get_bucket.bucket = None
        if get_bucket.bucket == None:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            get_bucket.bucket = s3.get_bucket( config.bucket_name )
            bucket_contents = Key(get_bucket.bucket)
        return get_bucket.bucket
    except Exception, e:
        log.critical( 'Failed to obtain s3 bucket: %s' % str(e) )
        raise

def download_file_from_s3( file_name, s3_key ):
    try:
        log.info( 'Downloading s3 file %s to: %s' % ( s3_key, file_name ) )
        bucket = get_bucket()
        k = Key( bucket )
        k.key = s3_key
        k.get_contents_to_filename( file_name )
    except Exception, e:
        log.critical( "Failed to download to file: '%s' From s3 key: '%s' Error was: %s" % ( file_name, s3_key, str( e ) ) )
        raise

