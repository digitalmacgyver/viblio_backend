import json
import os
import uuid

import boto
from boto.s3.key import Key

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

def get_exif( file_data, log, data = None ):
    media_file = file_data['ifile']
    exif_file = file_data['ofile']
   
    try:
        command = '/usr/local/bin/exiftool -j -w! _exif.json -c %+.6f ' + media_file
        log.info( 'Running exif extraction command: ' + command )
        os.system( command )
    except Exception as e:
        log.error( 'EXIF extraction failed, error was: ' + str( e ) )
        raise

    file_handle = open( exif_file )

    info = json.load( file_handle )

    exif_data = {}
    if info[0]:
        exif_data = info[0]

    file_ext     = str( exif_data.get( 'FileType', '' ) )
    mime_type    = str( exif_data.get( 'MIMEType', '' ) )
    lat          = exif_data.get( 'GPSLatitude', None )
    lng          = exif_data.get( 'GPSLongitude', None )
    rotation     = str( exif_data.get( 'Rotation', '0' ) )
    frame_rate   = str( exif_data.get( 'VideoFrameRate', '24' ) )
    create_date  = str( exif_data.get( 'MediaCreateDate', '' ) )
    image_width  = exif_data.get( 'ImageWidth', None)
    image_height = exif_data.get( 'ImageHeight', None)

    log.info( 'Returning from exif extraction.' )

    return( { 'file_ext'    : file_ext, 
              'mime_type'   : mime_type, 
              'lat'         : lat, 
              'lng'         : lng, 
              'create_date' : create_date, 
              'rotation'    : rotation, 
              'frame_rate'  : frame_rate,
              'width'       : image_width,
              'height'      : image_height
              } )

def rename_upload_with_extension( file_data, log, data = None ):
    '''Brewtus writes the uploaded file as <fileid> without an
    extenstion, but the info struct has an extenstion.  See if its
    something other than '' and if so, move the file under its
    extension so transcoding works.'''

    if 'fileExt' in data['info']:
        src = file_data['ifile']
        tar = src + data['info']['fileExt'].lower()
        if not src == tar:
            try:
                os.rename( src, tar )
                return tar
            except Exception as e:
                log.error( "Failed to rename %s to %s" % ( src, tar ) )
                raise

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
