import commands
import json
import logging
import os
import re

import vib.utils.s3 as s3

log = logging.getLogger( __name__)

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

def get_exif( media_uuid, filename ):   
    try:
        exif_file = os.path.splitext( filename )[0] + '_exif.json'
        command = '/usr/local/bin/exiftool -j -w! _exif.json -c %+.6f ' + filename
        log.info( json.dumps( {
                    'media_uuid' : media_uuid,
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
        duration     = exif_data.get( 'Duration', None )

        if duration is not None:
            match = re.match( r'(\d+):(\d\d):(\d\d)', duration )
            if match is not None:
                ( hours, minutes, secs ) = match.groups()
                duration = int( hours )*60*60 + int( minutes )*60 + int( secs )
            else:
                duration = None

        return {  'file_ext'    : file_ext, 
                  'mime_type'   : mime_type, 
                  'lat'         : lat, 
                  'lng'         : lng, 
                  'create_date' : create_date, 
                  'rotation'    : rotation, 
                  'frame_rate'  : frame_rate,
                  'width'       : image_width,
                  'height'      : image_height,
                  'duration'    : duration
                  }

    except Exception as e:
        log.error( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : 'EXIF extraction failed, error was: %s' % e
                    } ) )
        raise

def move_atom( media_uuid, filename ):
    '''Attempt to relocate the atom to the start of the file.'''

    cmd = '/usr/local/bin/qtfaststart %s' % filename
    log.info( cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    output = output.decode( 'utf-8' )
    if status != 0 or not os.path.isfile( filename ):
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

def transcode_and_store( media_uuid, input_filename, outputs, exif ):
    '''Takes in a media_id, input filename on the filesystem, the
    outputs data structure sent to a Transcode job, and the exif data
    associated with the input filename.

    Returns the outputs data structure augmented with _fs locations
    for the generated files.
    '''

    rotation = exif['rotation']
    mimetype = exif['mime_type']

    ffopts = ' -c:a libfdk_aac '
    
    log_message = ''
    cmd_output = ''

    if rotation == '90':
        log_message = 'Video is rotated 90 degrees, rotating.'
        ffopts += ' -vf transpose=1 -metadata:s:v:0 rotate=0 '
    elif rotation == '180':
        log_message = 'Video is rotated 180 degrees, rotating.'
        ffopts += ' -vf hflip,vflip -metadata:s:v:0 rotate=0 '
    elif rotation == '270':
        log_message = 'Video is rotated 270 degrees, rotating.'
        ffopts += ' -vf transpose=2 -metadata:s:v:0 rotate=0 '
    else:
        log_message = 'Video is not rotated.'

    log.debug( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : log_message
                } ) )

    output_cmd = ""
    output_files_fs = []
    for idx, output in enumerate( outputs ):
        output_cmd += ffopts
        video_bit_rate = " -crf 22 -maxrate %sk -bufsize 4096k " % output.get( 'max_video_bitrate', 1500 )
        audio_bit_rate = " -b:a %sk " % output.get( 'audio_bitrate', 160 )
        output_file_fs = "%s/%s_%s.%s" % ( config.transcode_dir, media_uuid, idx, output.get( 'format', 'mp4' ) )
        output_cmd += video_bit_rate + audio_bit_rate + output_file_fs
        output_files_fs.append( output_file_fs )
        output['output_file_fs'] = output_file_fs
        
    cmd = '/usr/local/bin/ffmpeg -y -i %s %s' % ( input_filename, output_cmd )
    log.info( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : "Running FFMPEG command %s" % cmd
                } ) )
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    cmd_output = cmd_output.decode( 'utf-8' )

    log.debug( json.dumps( {
                'media_uuid' : media_uuid,
                'message' : "FFMPEG command output was: %s" % cmd_output
                } ) )

    valid_outputs = True
    for output_file_fs in output_files_fs:
        if not os.path.isfile( output_file_fs ):
            valid_outputs = False
            break
    if not valid_outputs or status != 0:
        log.error( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : 'Failed to generate transcoded video with: %s, error was ...%s' % ( cmd, cmd_output[-256:])
                    } ) )
        raise Exception( 'Failed to generate transcoded video: ...%s' % cmd_output[-256:] )

    # Generate posters and upload to S3
    for idx, output in enumerate( outputs ):
        log.info( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : "Uploading video for media_uuid %s file %s to S3 %s/%s" % ( media_uuid, output_files_fs[idx], output['output_file']['s3_bucket'], output['output_file']['s3_key'] )
                    } ) )
        s3.upload_file( output_files_fs[idx], output['output_file']['s3_bucket'], output['output_file']['s3_key'] )

        thumbnails = generate_thumbnails( media_uuid, output_files_fs[idx], output['thumbnails'] )
        output['thumbnails'] = thumbnails
        for idx, thumbnail in enumerate( output['thumbnails'] ):
            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'message' : "Uploading thumbnail for media_uuid %s file %s to S3 %s/%s" % ( media_uuid, thumbnail['output_file_fs'], thumbnail['output_file']['s3_bucket'], thumbnail['output_file']['s3_key'] )
                        } ) )
            s3.upload_file( thumbnail['output_file_fs'], thumbnail['output_file']['s3_bucket'], thumbnail['output_file']['s3_key'] )

    return outputs

def generate_thumbnails( media_uuid, input_file_fs, thumbnails ):
    '''Takes in a media_uuid, the path to an input movie file, and an
    array of thumbnail data structures.

    Generates the desired thumbnails, and returns a modified
    thumbnails data structure that includes output_file_fs elements
    for each thumbnail.'''

    exif = get_exif( media_uuid, input_file_fs )

    video_x = int( exif['width'] )
    video_y = int( exif['height'] )

    # DEBUG - for the time being we support only the first element of
    # the "times" key of the thumbnails data structure.

    for idx, thumbnail in enumerate( thumbnails ):
        output = ''

        time = thumbnail['times'][0]

        ffmpeg_opts = ' -vframes 1 '

        thumbnail_size = thumbnail.get( 'size', "320x180" )
        thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )
        thumbnail_x = int( thumbnail_x )
        thumbnail_y = int( thumbnail_y )
        thumbnail_aspect_ratio = float( thumbnail_x ) / float( thumbnail_y )

        if video_x and video_y:
            video_aspect_ratio = video_x / float( video_y )
    
            if video_aspect_ratio < thumbnail_aspect_ratio:
                ffmpeg_opts += ' -vf scale=-1:%s,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( thumbnail_y, thumbnail_x, thumbnail_y )
            else:
                ffmpeg_opts += ' -vf scale=%s:-1,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( thumbnail_x, thumbnail_x, thumbnail_y )
        else:
            ffmpeg_opts += ' -vf scale=%s:%s ' % ( thumbnail_x, thumbnail_y )

        thumbnail_file_fs = config.transcode_dir + "/" + media_uuid + "_%s_%s.%s" % ( thumbnail['label'], idx, thumbnail.get( 'format', 'png' ) )
        cmd = '/usr/local/bin/ffmpeg -y -ss %s -i %s %s %s' %( time, input_file_fs, ffmpeg_opts, thumbnail_file_fs )

        log.info( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : "Running command %s to generate thumbnail for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs )
                    } ) )

        ( status, output ) = commands.getstatusoutput( cmd )
        output = output.decode( 'utf-8' )

        log.debug( json.dumps( {
                    'media_uuid' : media_uuid,
                    'message' : "Thumbnail command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, output )
                    } ) )

        if status != 0 or not os.path.isfile( thumbnail_file_fs ):
            log.warning( json.dumps( {
                        'media_uuid' : media_uuid,
                        'message' : "Failed to generate scaled thumbnail for media_uuid %s, video file %s with command %s" % ( media_uuid, input_file_fs, cmd )
                        } ) )

            cmd = '/usr/local/bin/ffmpeg -y -ss %s -i %s -vframes 1 -vf scale=%s:%s %s' %( time, input_file_fs, thumbnail_x, thumbnail_y, thumbnail_file_fs )

            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'message' : "Running safer command %s to generate thumbnail for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs )
                        } ) )

            ( status, output ) = commands.getstatusoutput( cmd )
            output = output.decode( 'utf-8' )

            log.debug( json.dumps( {
                        'media_uuid' : media_uuid,
                        'message' : "Thumbnail command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, output )
                        } ) )

            if status != 0 or not os.path.isfile( thumbnail_file_fs ):
                log.error( json.dumps( {
                            'media_uuid' : media_uuid,
                            'message' : "Failed to generate thumbnail for media_uuid %s, video file %s with command %s, error was ...%s" % ( media_uuid, input_file_fs, cmd, output[-256:] )
                            } ) )
                raise Exception( 'Failed to generate thumbnail ...%s' % output[-256:] )
            else:
                thumbnail['output_file_fs'] = thumbnail_file_fs 
        else:
            thumbnail['output_file_fs'] = thumbnail_file_fs 

    return thumbnails
