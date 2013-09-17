import json
import os

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

def get_exif( ifile, ofile, log, data = None ):
    media_file = ifile
    exif_file = ofile
   
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



def rename_upload_with_extension( main_files, info, log, data = None ):
    '''Brewtus writes the uploaded file as <fileid> without an
    extenstion, but the info struct has an extenstion.  See if its
    something other than '' and if so, move the file under its
    extension so transcoding works.'''

    if 'fileExt' in info:
        src = main_files['ifile']
        tar = src + info['fileExt'].lower()
        if not src == tar:
            try:
                os.rename( src, tar )
                main_files['ifile'] = tar
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
        log.info( 'Got s3 bucket.' )
        return __get_bucket.bucket
    except Exception as e:
        log.error( 'Failed to obtain s3 bucket: %s' % str(e) )
        raise

def upload_file( file_data, log, data = None ):
    '''Upload a file to S3'''
    try:
        bucket = __get_bucket( log )

        log.info( 'Uploading %s to s3: %s' % ( file_data['output'], file_data['key'] ) )
        bucket_contents.key = file_data['key']
        bucket_contents.set_contents_from_filename( file_data['output'] )
    except Exception as e:
        log.error( 'Failed to upload to s3: %s' % str( e ) )
        raise

'''
def lc_extension( basename, ext ):

    lc_ext = ext.lower()
    if lc_ext != ext:
        os.rename( basename + ext, basename + lc_ext )

    return basename, lc_ext

def create_filenames (full_filename):
    # Basename includes the absolute path and everything up to the extension.
    basename, ext = os.path.splitext( full_filename )
    # Rename the file so its extension is in lower case.
    basename, ext = lc_extension( basename, ext )
    # By convention the filename is the media_uuid.
    media_uuid = os.path.split( basename )[1]
    input_video = full_filename
    input_info = basename + '.json'
    input_metadata = basename + '_metadata.json'
    # Output file names
    output_video = basename + '.mp4'
    avi_video = basename + '.avi'
    output_thumbnail = basename + '_thumbnail.jpg'
    output_poster = basename + '_poster.jpg'
    output_metadata = input_metadata
    output_face = basename + '_face0.jpg'
    output_exif = basename + '_exif.json'
    
    video_key = media_uuid + '/' + os.path.basename( output_video )
    avi_key = media_uuid + '/' + os.path.basename( avi_video )
    thumbnail_key = media_uuid + '/' + os.path.basename( output_thumbnail )
    poster_key = media_uuid + '/' + os.path.basename( output_poster )
    metadata_key = media_uuid + '/' + os.path.basename( output_metadata )
    face_key = media_uuid + '/' + os.path.basename( output_face )
    exif_key = media_uuid + '/' + os.path.basename( output_exif )
    filenames = {
        'uuid': media_uuid, # Used to insert the row in the database, just the basename of the input file.
        'info': input_info, # Brewtus metadata from the file, basename+.json
        'video_key': video_key, # S3 key for main = uid / uid.mp4 filename
        'avi_key': avi_key, # S3 key for avi = uid / uid.avi
        'thumbnail_key': thumbnail_key, # S3 key for thumbnail = uid / uid_thumbnail.jpg
        'poster_key': poster_key, # S3 key for poster = uid / uid_poster.jpg
        'metadata_key': metadata_key, # S3 key for metadata created by uploader = uid / uid_metadata.json
        'face_key': face_key, # S3 key for a single face found in the video, by convention.
        'exif_key': exif_key, # S3 key for exif data = uid / uid_exif.json
        'avi' : {
            'input': output_video,
            'output': avi_video
            },
        'video': {
            'input': input_video,
            'output': output_video
            },
        'thumbnail': {
            'input': output_video,
            'output': output_thumbnail
            },
        'poster': {
            'input': output_video,
            'output': output_poster
            },
        'metadata': {
            'input': input_metadata,
            'output': output_metadata
            },
        'face': {
            'input': output_video,
            'output': output_face
            },
        'exif': {
            'output': output_exif
            }
        }
    return(filenames)
'''
