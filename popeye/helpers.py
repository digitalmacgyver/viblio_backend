import json
import ntpath
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


def get_iv_tracks( files, log, data ):
    return '{"tracks": {"file_id": "64", "numberoftracks": "11", "track": [{"trackid": "0", "personid": "50", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_00_50.jpg", "starttime": "2013-10-05 13:16:54", "endtime": "2013-10-05 13:16:54", "width": "378", "height": "378", "facecenterx": "782", "facecentery": "339", "detectionscore": "6", "recognitionconfidence": "75.94"}, {"trackid": "1", "personid": "91", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_01_91.jpg", "starttime": "2013-10-05 13:17:10", "endtime": "2013-10-05 13:17:10", "width": "340", "height": "340", "facecenterx": "297", "facecentery": "204", "detectionscore": "4", "recognitionconfidence": "75.53"}, {"trackid": "2", "personid": "77", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_02_77.jpg", "starttime": "2013-10-05 13:17:21", "endtime": "2013-10-05 13:17:21", "width": "314", "height": "314", "facecenterx": "216", "facecentery": "181", "detectionscore": "27", "recognitionconfidence": "75.53"}, {"trackid": "3", "personid": "77", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_03_77.jpg", "starttime": "2013-10-05 13:17:36", "endtime": "2013-10-05 13:17:37", "width": "390", "height": "390", "facecenterx": "747", "facecentery": "319", "detectionscore": "34", "recognitionconfidence": "76.16"}, {"trackid": "4", "personid": "38", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_04_38.jpg", "starttime": "2013-10-05 13:18:07", "endtime": "2013-10-05 13:18:07", "width": "389", "height": "389", "facecenterx": "949", "facecentery": "215", "detectionscore": "5", "recognitionconfidence": "76.11"}, {"trackid": "8", "personid": "50", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_08_50.jpg", "starttime": "2013-10-05 13:15:16", "endtime": "2013-10-05 13:15:17", "width": "378", "height": "378", "facecenterx": "782", "facecentery": "339", "detectionscore": "6", "recognitionconfidence": "75.94"}, {"trackid": "9", "personid": "91", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_09_91.jpg", "starttime": "2013-10-05 13:15:32", "endtime": "2013-10-05 13:15:32", "width": "340", "height": "340", "facecenterx": "297", "facecentery": "204", "detectionscore": "4", "recognitionconfidence": "75.53"}, {"trackid": "10", "personid": "77", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_10_77.jpg", "starttime": "2013-10-05 13:15:43", "endtime": "2013-10-05 13:15:43", "width": "314", "height": "314", "facecenterx": "216", "facecentery": "181", "detectionscore": "27", "recognitionconfidence": "75.53"}, {"trackid": "11", "personid": "77", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_11_77.jpg", "starttime": "2013-10-05 13:15:58", "endtime": "2013-10-05 13:15:59", "width": "390", "height": "390", "facecenterx": "747", "facecentery": "319", "detectionscore": "34", "recognitionconfidence": "76.16"}, {"trackid": "12", "personid": "46", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_12_46.jpg", "starttime": "2013-10-05 13:16:28", "endtime": "2013-10-05 13:16:29", "width": "389", "height": "389", "facecenterx": "947", "facecentery": "320", "detectionscore": "13", "recognitionconfidence": "76.25"}, {"trackid": "13", "personid": "46", "bestfaceframe": "b1be9a20-2d7c-11e3-a8d4-255b428c4f8c/b1be9a20-2d7c-11e3-a8d4-255b428c4f8c_face_13_46.jpg", "starttime": "2013-10-05 13:16:41", "endtime": "2013-10-05 13:16:41", "width": "276", "height": "276", "facecenterx": "154", "facecentery": "221", "detectionscore": "15", "recognitionconfidence": "76.25"}]}}'
