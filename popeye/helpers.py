import json
#import logging
import os

#from appconfig import AppConfig
#config = AppConfig( 'popeye' ).config()
#logging.basicConfig( filename = config['logfile'], level = config.loglevel )
#log = logging.getLogger( __name__ )

def perror( log, msg ):
#    log.error( msg )
    return { 'error': True, 'message': msg }

def exif( filenames ):
    media_file = filenames['video']['input']
    exif_file = filenames['exif']['output']
   
    try:
        command = '/usr/local/bin/exiftool -j -w! _exif.json -c %+.6f ' + media_file
        os.system( command )
    except Exception as e:
        print 'EXIF extraction failed, error was: %s' % str( e )
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

def lc_extension( basename, ext ):
    '''Lowercase the extension of our input file, and rename the file
    to match.'''

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
        'uuid': media_uuid,
        'info': input_info,
        'video_key': video_key,
        'avi_key': avi_key,
        'thumbnail_key': thumbnail_key,
        'poster_key': poster_key,
        'metadata_key': metadata_key,
        'face_key': face_key,
        'exif_key': exif_key,
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

def handle_errors( filenames ):
    '''Copy temporary files to error directory.'''
    try:
#        log.info( 'Error occured, relocating temp files to error directory...' )
        for f in ['video','thumbnail','poster','metadata','face','exif','avi']:
            if ( f in filenames ) and ( 'output' in filenames[f] ) and os.path.isfile( filenames[f]['output'] ):
                full_name = filenames[f]['output']
                base_path = os.path.split( full_name )[0]
                file_name = os.path.split( full_name )[1]
                os.rename( filenames[f]['output'], base_path + '/errors/' + file_name )
            if ( f in filenames ) and ( 'input' in filenames[f] ) and os.path.isfile( filenames[f]['input'] ):
                full_name = filenames[f]['input']
                base_path = os.path.split( full_name )[0]
                file_name = os.path.split( full_name )[1]
                os.rename( filenames[f]['input'], base_path + '/errors/' + file_name )
        full_name = filenames['info']
        base_path = os.path.split( full_name )[0]
        file_name = os.path.split( full_name )[1]
        os.rename( filenames['info'], base_path + '/errors/' + file_name )
    except Exception as e_inner:
#        log.error( 'Some trouble relocating temp files temp files: %s' % str( e_inner ) )
        pass
