import commands
import logging
import os

log = logging.getLogger( __name__)

def get_exif( filename ):   
    try:
        exif_file = filename + '_exif.json'
        command = '/usr/local/bin/exiftool -j -w! _exif.json -c %+.6f ' + media_file
        log.info( json.dumps( {
                    'message' : 'Running exif extraction command: %s' % command
                    } ) )
        os.system( command )

        file_handle = open( exif_file )
        info = json.load( file_handle )
        file_handle.close()
        os.remove( exif_file )

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

    except Exception as e:
        log.error( json.dumps( {
                    'EXIF extraction failed, error was: %s' % e
                    } ) )
        raise

def transcode( media_uuid, input_filename, outputs, exif ):
    rotation = exif['rotation']
    mimetype = exif['mimetype']

    # DEBUG - Presently we ignore the size directive.
    
    ffopts = ' -c:a libfdk_aac '
    
    log_message = ''

    if rotation == '90':
        log_message = 'Video is rotated 90 degrees, rotating.'
        ffopts += ' -vf transpose=1 -metadata:s:v:0 rotate=0 '
    elif rotation == '180':
        log_message 'Video is rotated 180 degrees, rotating.'
        ffopts += ' -vf hflip,vflip -metadata:s:v:0 rotate=0 '
    elif rotation == '270':
        log_message = 'Video is rotated 270 degrees, rotating.'
        ffopts += ' -vf transpose=2 -metadata:s:v:0 rotate=0 '

    log.info( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : log_message
                } ) )

    output_cmd = ""
    output_files = []
    for idx, output in enumerate( outputs ):
        output_cmd += ffopts
        video_bit_rate = " -b:v %sk " % output.get( 'max_video_bitrate', 1500 )
        audio_bit_rate = " -b:a %sk " % output.get( 'audio_bitrate', 160 )
        output_file = " %s/%s_%s.%s " ( config.transcode_dir, media_uuid, idx, output.get( 'format', 'mp4' ) )
        output_cmd += video_bit_rate + audio_bit_rate + output_file
        output_files.append( output_file )

    cmd = '/usr/local/bin/ffmpeg -y -i %s %s' % ( input_filename, output_cmd )
    log.info( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : "Running FFMPEG command %s" % output_cmd
                } ) )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : "FFMPEG command output was: %s" % output
                } ) )

    valid_outputs = True
    for output_file in output_files:
        if not os.path.isfile( output_file ):
            valid_outputs = False
            break
    if not valid_outputs or status != 0:
        log.error( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : 'Failed to generate transcoded video with: %s' % cmd
                    } ) )
        raise Exception( 'Failed to generate transcoded video with: %s' % cmd )

    # Generate posters
    # Store to S3


def move_atom( media_uuid, filename ):
    '''Attempt to relocate the atom to the start of the file.'''

    cmd = '/usr/local/bin/qtfaststart %s' % filename
    log.info( cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    if status != 0 or not os.path.isfile( ofile ):
        log.warning( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : 'Failed to run qtfaststart on %s' % filename
                    } ) )
    else:
        log.warning( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : 'qtfaststart command returned successful completion status for filename: %s' % filename
                    } ) )
    return

def generate_poster( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    width    = data['transcoded_exif']['width']
    height   = data['transcoded_exif']['height']

    ffmpeg_opts = ' -vframes 1 '

    if width and height:
        aspect_ratio = width/float(height)
        log.info( 'Poster aspect ratio is ' + str( aspect_ratio ) )
    
        if aspect_ratio < 16/float(9):
            ffmpeg_opts += ' -vf scale=-1:180,pad="320:180:(ow-iw)/2:(oh-ih)/2" '
        else:
            ffmpeg_opts += ' -vf scale=320:-1,pad="320:180:(ow-iw)/2:(oh-ih)/2" '
    else:
        log.warning( 'Could not get width and height for transcoded video.' )
        ffmpeg_opts += ' -vf scale=320:180 '

    cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s %s %s' %( ifile, ffmpeg_opts, ofile )

    log.info( 'Executing poster generation command: '+ cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        log.warning( 'Failed to generate poster with command: %s' % cmd )

        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=320:180 %s' %( ifile, ofile )
        log.info( 'Executing safer poster generation command: '+ cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        log.debug( 'Command output was: ' + output )            
        if status != 0 or not os.path.isfile( ofile ):
            raise Exception( 'Failed to generate poster with command: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )        
        
def generate_thumbnail( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    width    = data['transcoded_exif']['width']
    height   = data['transcoded_exif']['height']    

    ffmpeg_opts = ' -vframes 1 '

    if width and height:
        if width > height:
            ffmpeg_opts += ' -vf scale=128:-1,pad="128:128:(ow-iw)/2:(oh-ih)/2" '
        else:
            ffmpeg_opts += ' -vf scale=-1:128,pad="128:128:(ow-iw)/2:(oh-ih)/2" '
    else:
        log.warning( 'No width and height information available in transcoded exif' )
        ffmpeg_opts += ' -vf scale=128:128 '

    cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s %s %s' %( ifile, ffmpeg_opts, ofile )

    log.info( 'Executing thumbnail generation command: ' + cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        log.warning( 'Failed to generate thumbnail with command: %s' % cmd )

        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=320:180 %s' %( ifile, ofile )
        log.info( 'Executing safer thumbnail generation command: '+ cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        log.debug( 'Command output was: ' + output )            
        if status != 0 or not os.path.isfile( ofile ):
            raise Exception( 'Failed to generate thumbnail with command: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )

