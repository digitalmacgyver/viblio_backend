import boto
from boto.s3.key import Key
import json
import logging
from logging import handlers

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 's3: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def upload_file( filename, bucket, key ):
    '''Upload the file at filename to s3 in bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        k = Key( bucket )

        log.info( json.dumps( { 
                    'message' : 'Uploading %s to s3: %s/%s' % ( filename, bucket, key )
                              } ) )

        k.key = key

        k.set_contents_from_filename( filename )

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to upload %s to s3: %s/%s' % ( filename, bucket, key )
                              } ) )
        raise

def upload_string( string, bucket, key ):
    '''Store the string to s3 in bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        k = Key( bucket )

        log.info( json.dumps( { 
                    'message' : 'Storing string in s3: %s/%s' % ( bucket, key )
                              } ) )

        k.key = key

        k.set_contents_from_string( string )

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to store string to s3: %s/%s' % ( bucket, key )
                              } ) )
        raise


def download_file( filename, bucket, key ):
    '''Download to the file at filename the contents of s3 in bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        k = Key( bucket )

        log.info( json.dumps( { 
                    'message' : 'Downloading %s from s3: %s/%s' % ( filename, bucket, key )
                              } ) )

        k.key = key

        k.get_contents_to_filename( filename )

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to download %s from s3: %s/%s' % ( filename, bucket, key )
                              } ) )
        raise

def download_string( bucket, key ):
    '''Download to the file at filename the contents of s3 in bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        k = Key( bucket )

        log.info( json.dumps( { 
                    'message' : 'Downloading as string from s3: %s/%s' % ( bucket, key )
                              } ) )

        k.key = key

        string = k.get_contents_as_string()

        return string

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to download string from s3: %s/%s' % ( bucket, key )
                              } ) )
        raise

def copy_s3_file( source_bucket, source_key, target_bucket, target_key ):
    '''Copy the source file in S3 to the target file'''
    try:
        log.info( json.dumps( { 
                    'message' : 'Copying S3 file from: %s/%s to: %s/%s' % ( source_bucket, source_key, target_bucket, target_key )
                              } ) )

        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )

        if source_bucket == target_bucket:
            bucket = s3.get_bucket( source_bucket )
            bucket.copy_key( target_key, source_bucket, source_key )
        else:
            k = Key( s3.get_bucket( source_bucket ), source_key )
            k.copy( s3.get_bucket( target_bucket ), target_key )

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to copy S3 file from: %s/%s to: %s/%s, error: %s' % ( source_bucket, source_key, target_bucket, target_key, e )
                    } ) )
        raise

def delete_s3_file( bucket, key ):
    '''Delete the file at bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        k = Key( bucket )

        log.info( json.dumps( { 
                    'message' : 'Deleting file from s3: %s/%s' % ( bucket, key )
                              } ) )

        k.key = key

        k.delete()

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to delete file from s3: %s/%s with error: %s' % ( bucket, key, e )
                    } ) )
        raise

def delete_s3_files( bucket, keys ):
    '''Delete all files in keys in bucket, keys must be less than 1000
    elements'''
    try:

        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )

        log.info( json.dumps( { 
                    'message' : 'Deleting files from s3 bucket %s' % ( bucket )
                    } ) )

        bucket.delete_keys( keys[:1000], quiet=True )

    except Exception as e:
        log.error( json.dumps( { 
                    'message' : 'Failed to delete files from s3 bucket: %s with error: %s' % ( bucket, e )
                    } ) )
        raise

def check_exists( bucket, key ):
    '''Upload the file at filename to s3 in bucket/key'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        return bucket.get_key( key )
    except Exception as e:
        log.error( json.dumps( { 'message' : 'Failed to determine whether key %s exists in bucket %s' % ( key, bucket ) } ) )
        raise

def _get_bucket( bucket ):
    '''Just get the bucket.'''
    try:
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket( bucket )
        return bucket
    except Exception as e:
        log.error( json.dumps( { 'message' : 'Failed to get bucket %s' % ( bucket ) } ) )
        raise
