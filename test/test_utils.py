import os
import sys
sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'create_test_data' ).config()

from models import *

import boto
from boto.s3.key import Key

import logging

logging.basicConfig( filename = config['logfile'], level = config.loglevel )

log = logging.getLogger( __name__ )

log.critical( "WHEE - test utils" )

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
        
