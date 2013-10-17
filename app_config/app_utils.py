import datetime
from datetime import timedelta
import json
import logging
import os
import random
import re
import sys
import uuid

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'app_config' ).config()

logging.basicConfig( filename = config['logfile'], level = config.loglevel )
log = logging.getLogger( __name__ )
screen_output = logging.StreamHandler( sys.stdout )
screen_output.setLevel( logging.INFO )
log.addHandler( screen_output )

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

def show_configuration( engine ):
    '''Print out all configuration data in database.'''
    try:
        conn = _get_conn( engine )
        meta = _get_meta( engine )
        app_configs = meta.tables['app_configs']
        
        fields = ['app','version_string','feature','enabled','current','config','created_date','updated_date']

        header = ",".join( fields )
        print header

        for app_config in conn.execute( select( [app_configs] ) ):
            config_fields = []
            for field in fields:
                cf = app_config[field]
                if cf == None:
                    cf = 'NULL'
                config_fields.append( str( cf ) )
            config_string = ','.join( config_fields )
            print config_string

    except Exception as e:
        log.error( 'Error printing configuration: ' + str( e ) )
        raise

def upload_app_file( engine, app, version_string, input_file ):
    try:
        # Check if version string conforms to standards.
        log.info( "Validating the version string contains only letters and numbers. [._-]" )
        if re.match( '^[\w\._-]+$', version_string ):
            log.info( 'Version string validated' )
        else:
            error = 'Invalid version string, only alphanumeric and .-_ are allowed.'
            log.error( error )
            raise Exception( error )

        # Check if input file exists and is readable.
        log.info( "Validating input file: " + input_file )
        if _check_file( input_file ):
            log.info( 'Input file validated.' )
        else:
            error = 'Invalid input file, file must exist and be readable.'
            log.error( error )
            raise Exception( error )

        # Upload the file to S3
        log.info( 'Calculating S3 key for ' + input_file )
        s3_key = version_string + "/" + os.path.basename( input_file )
        upload_file_to_s3( input_file, s3_key )

        uri = json.dumps( { 'uri' : config.bucket_name + '/' + s3_key, size : os.path.getsize( input_file ) } )

        try:
            log.info( "Updating database" )
            conn = _get_conn( engine ) 
            meta = _get_meta( engine )
            # Begin transaction
            trans = conn.begin()
            app_configs = meta.tables['app_configs']

            # Update prior versions set current = false
            log.info( "Setting other verions of %s to current = false" % app )
            conn.execute( app_configs.update().where( app_configs.c.app == app ).values( current = False ) )
            
            log.info( "Inserting new version %s to database" % version_string )
            result = conn.execute( app_configs.insert(),
                                   id = None,
                                   app = app,
                                   version_string = version_string,
                                   current = True,
                                   config = uri )
            log.info( "Inserted primary key ID was " + str( result.inserted_primary_key[0] ) )
                          
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise

    except Exception as e:
        log.error( 'Error uploading app file: ' + str( e ) )
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
        
