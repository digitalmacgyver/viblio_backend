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


def get_iv_tracks( files, log, data ):
    return '{"tracks": {"numberoftracks": "22", "track": [{"trackid": "0", "personid": "0", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_20-09-2013_12-22-52-583_0.jpg", "starttime": "2013-09-18 04:58:03", "endtime": "2013-09-18 04:58:04", "width": "860", "height": "860", "facecenterx": "483", "facecentery": "783", "detectionscore": "5", "recognitionconfidence": "85.11"}, {"trackid": "1", "personid": "0", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-58-11-533_1.jpg", "starttime": "2013-09-18 04:58:11", "endtime": "2013-09-18 04:58:12", "width": "786", "height": "786", "facecenterx": "510", "facecentery": "784", "detectionscore": "5", "recognitionconfidence": "80.99"}, {"trackid": "2", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-58-17-579_2.jpg", "starttime": "2013-09-18 04:58:17", "endtime": "2013-09-18 04:58:18", "width": "173", "height": "173", "facecenterx": "383", "facecentery": "993", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "3", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-58-35-949_3.jpg", "starttime": "2013-09-18 04:58:35", "endtime": "2013-09-18 04:58:36", "width": "765", "height": "765", "facecenterx": "510", "facecentery": "812", "detectionscore": "7", "recognitionconfidence": "0.00"}, {"trackid": "4", "personid": "0", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-58-55-133_4.jpg", "starttime": "2013-09-18 04:58:55", "endtime": "2013-09-18 04:58:55", "width": "804", "height": "804", "facecenterx": "502", "facecentery": "823", "detectionscore": "4", "recognitionconfidence": "83.04"}, {"trackid": "5", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-59-08-871_5.jpg", "starttime": "2013-09-18 04:59:08", "endtime": "2013-09-18 04:59:09", "width": "157", "height": "157", "facecenterx": "417", "facecentery": "1057", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "6", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-59-16-568_6.jpg", "starttime": "2013-09-18 04:59:16", "endtime": "2013-09-18 04:59:17", "width": "177", "height": "177", "facecenterx": "249", "facecentery": "1403", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "7", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-59-33-747_7.jpg", "starttime": "2013-09-18 04:59:33", "endtime": "2013-09-18 04:59:34", "width": "778", "height": "778", "facecenterx": "517", "facecentery": "849", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "8", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-59-36-689_8.jpg", "starttime": "2013-09-18 04:59:36", "endtime": "2013-09-18 04:59:37", "width": "778", "height": "778", "facecenterx": "517", "facecentery": "849", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "10", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_04-59-50-135_10.jpg", "starttime": "2013-09-18 04:59:50", "endtime": "2013-09-18 04:59:50", "width": "690", "height": "690", "facecenterx": "494", "facecentery": "839", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "11", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-00-713_11.jpg", "starttime": "2013-09-18 05:00:00", "endtime": "2013-09-18 05:00:01", "width": "707", "height": "707", "facecenterx": "490", "facecentery": "830", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "12", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-18-510_12.jpg", "starttime": "2013-09-18 05:00:18", "endtime": "2013-09-18 05:00:18", "width": "88", "height": "88", "facecenterx": "530", "facecentery": "1646", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "13", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-18-510_13.jpg", "starttime": "2013-09-18 05:00:18", "endtime": "2013-09-18 05:00:18", "width": "718", "height": "718", "facecenterx": "537", "facecentery": "824", "detectionscore": "5", "recognitionconfidence": "0.00"}, {"trackid": "14", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-22-053_14.jpg", "starttime": "2013-09-18 05:00:22", "endtime": "2013-09-18 05:00:22", "width": "765", "height": "765", "facecenterx": "539", "facecentery": "798", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "15", "personid": "0", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-30-876_15.jpg", "starttime": "2013-09-18 05:00:30", "endtime": "2013-09-18 05:00:31", "width": "780", "height": "780", "facecenterx": "565", "facecentery": "799", "detectionscore": "4", "recognitionconfidence": "80.71"}, {"trackid": "16", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-44-254_16.jpg", "starttime": "2013-09-18 05:00:44", "endtime": "2013-09-18 05:00:44", "width": "60", "height": "60", "facecenterx": "836", "facecentery": "1332", "detectionscore": "5", "recognitionconfidence": "0.00"}, {"trackid": "17", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-48-149_17.jpg", "starttime": "2013-09-18 05:00:48", "endtime": "2013-09-18 05:00:48", "width": "726", "height": "726", "facecenterx": "519", "facecentery": "796", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "18", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-00-52-076_18.jpg", "starttime": "2013-09-18 05:00:52", "endtime": "2013-09-18 05:00:52", "width": "82", "height": "82", "facecenterx": "282", "facecentery": "700", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "19", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-01-04-368_19.jpg", "starttime": "2013-09-18 05:01:04", "endtime": "2013-09-18 05:01:04", "width": "746", "height": "746", "facecenterx": "490", "facecentery": "774", "detectionscore": "4", "recognitionconfidence": "0.00"}, {"trackid": "20", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-01-17-490_20.jpg", "starttime": "2013-09-18 05:01:17", "endtime": "2013-09-18 05:01:17", "width": "69", "height": "69", "facecenterx": "285", "facecentery": "678", "detectionscore": "5", "recognitionconfidence": "0.00"}, {"trackid": "21", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_18-09-2013_05-01-21-448_21.jpg", "starttime": "2013-09-18 05:01:21", "endtime": "2013-09-18 05:01:21", "width": "745", "height": "745", "facecenterx": "484", "facecentery": "755", "detectionscore": "5", "recognitionconfidence": "0.00"}, {"trackid": "22", "personid": "-1", "bestfaceframe": "http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam17_19-09-2013_05-26-33-830_22.jpg", "starttime": "2013-09-19 05:26:33", "endtime": "2013-09-19 05:26:34", "width": "745", "height": "745", "facecenterx": "484", "facecentery": "755", "detectionscore": "5", "recognitionconfidence": "0.00"}]}}'
