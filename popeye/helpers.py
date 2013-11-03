import json
import ntpath
import os
import uuid

import boto
from boto.s3.key import Key

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

def __get_bucket( log ):
    try:
        if not hasattr( __get_bucket, "bucket" ):
            __get_bucket.bucket = None
        if __get_bucket.bucket == None:
            s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
            __get_bucket.bucket = s3.get_bucket( config.bucket_name )
            bucket_contents = Key( __get_bucket.bucket )
        log.debug( 'Got s3 bucket.' )
        return __get_bucket.bucket
    except Exception as e:
        log.error( 'Failed to obtain s3 bucket: %s' % str(e) )
        raise

def upload_file( file_data, log, data = None ):
    '''Upload a file to S3'''
    try:
        bucket = __get_bucket( log )
        k = Key( bucket )

        log.info( 'Uploading %s to s3: %s' % ( file_data['ofile'], file_data['key'] ) )
        k.key = file_data['key']
        k.set_contents_from_filename( file_data['ofile'] )
    except Exception as e:
        log.error( 'Failed to upload to s3: %s' % str( e ) )
        raise

