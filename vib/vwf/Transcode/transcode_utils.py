import commands
import glob
import json
import logging
import os
import re

import vib.rekog.utils as rekog
import vib.utils.s3 as s3

log = logging.getLogger( __name__)

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

def get_exif( media_uuid, filename ):   
    try:
        exif_file = os.path.splitext( filename )[0] + '_exif.json'
        command = '/usr/local/bin/exiftool -j -w! _exif.json -c %+.6f ' + filename
        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                'message' : 'Running exif extraction command: %s' % command } ) )

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
                match = re.match( r'([\d\.]+)\s+s', duration )
                if match is not None:
                    duration = float( match.groups()[0] )
                else:
                    duration = None

        if duration is None:
            # Try another way...
            try:
                ( status, output ) = commands.getstatusoutput( "ffprobe -v quiet -print_format json -show_format -show_streams %s" % ( filename ) )
                info = json.loads( output )
                duration = float( info['format']['duration'] )
            except:
                # Oh well...
                pass
        
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
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'message' : 'EXIF extraction failed, error was: %s' % e } ) )
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

    output_frame_rate = ' -r 30000/1001 '

    ffopts = ' -c:a libfdk_aac ' + output_frame_rate
    
    log_message = ''
    cmd_output = ''

    duration = exif.get( 'duration', None )
    image_fps = .2
    if duration and duration < 20:
        image_fps = 4.0 / duration
    elif duration and duration > 150:
        image_fps = 30.0 / duration

    image_opts = ''

    if rotation == '90':
        log_message = 'Video is rotated 90 degrees, rotating.'
        ffopts += ' -metadata:s:v:0 rotate=0 -vf transpose=1'
        image_opts += ' -metadata:s:v:0 rotate=0 -vf transpose=1,'
    elif rotation == '180':
        log_message = 'Video is rotated 180 degrees, rotating.'
        ffopts += ' -metadata:s:v:0 rotate=0 -vf hflip,vflip'
        image_opts += ' -metadata:s:v:0 rotate=0 -vf hflip,vflip,'
    elif rotation == '270':
        log_message = 'Video is rotated 270 degrees, rotating.'
        ffopts += ' -metadata:s:v:0 rotate=0 -vf transpose=2'
        image_opts += ' -metadata:s:v:0 rotate=0 -vf transpose=2,'
    else:
        log_message = 'Video is not rotated.'
        image_opts += ' -vf '

    image_opts += 'fps=%s ' % ( image_fps )

    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                             'message' : log_message } ) )


    output_cmd = ""
    output_files_fs = []
    for idx, output in enumerate( outputs ):
        output_cmd += ffopts
        if output.get( 'scale', None ) is not None:
            if rotation in [ '90', '180', '270' ]:
                output_cmd += ',scale="%s" ' % ( output.get( 'scale' ) )
            else:
                output_cmd += ' -vf scale="%s" ' % ( output.get( 'scale' ) )
        else:
            output_cmd += ' '
        video_bit_rate = " -crf 18 -maxrate %sk -bufsize 4096k " % output.get( 'max_video_bitrate', 1500 )
        audio_bit_rate = " -b:a %sk " % output.get( 'audio_bitrate', 160 )
        output_file_fs = "%s/%s_%s.%s" % ( config.transcode_dir, media_uuid, idx, output.get( 'format', 'mp4' ) )
        output_cmd += video_bit_rate + audio_bit_rate + output_file_fs
        output_files_fs.append( output_file_fs )
        output['output_file_fs'] = output_file_fs
        
    # Add in a hard coded command to get some high resolution, rotated
    # images for making albums.
    output_cmd += image_opts + ' -qscale:v 2 %s/%s-image-%%04d.jpg' % ( config.transcode_dir, media_uuid )

    cmd = '/usr/local/bin/ffmpeg -y -i %s %s' % ( input_filename, output_cmd )
    log.info( json.dumps( { 'media_uuid' : media_uuid,
                            'message' : "Running FFMPEG command %s" % cmd } ) )
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    cmd_output = cmd_output.decode( 'utf-8' )

    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                             'message' : "FFMPEG command output was: %s" % cmd_output } ) )

    input_frames = re.findall( r'frame=\s*(\d+)\s', cmd_output )

    valid_outputs = True
    for output_file_fs in output_files_fs:
        if not os.path.isfile( output_file_fs ):
            valid_outputs = False
            break
    if not valid_outputs or status != 0:
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'message' : 'Failed to generate transcoded video with: %s, error was ...%s' % ( cmd, cmd_output[-256:]) } ) )
        raise Exception( 'Failed to generate transcoded video: ...%s' % cmd_output[-256:] )

    # Generate posters and upload to S3
    for idx, output in enumerate( outputs ):
        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                'message' : "Uploading video for media_uuid %s file %s to S3 %s/%s" % ( media_uuid, output_files_fs[idx], output['output_file']['s3_bucket'], output['output_file']['s3_key'] ) } ) )

        s3.upload_file( output_files_fs[idx], output['output_file']['s3_bucket'], output['output_file']['s3_key'] )

        if 'thumbnails' in output:
            thumbnails = generate_thumbnails( media_uuid, output_files_fs[idx], output['thumbnails'], input_frames )
            output['thumbnails'] = thumbnails
            for idx, thumbnail in enumerate( output['thumbnails'] ):
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Uploading thumbnail for media_uuid %s file %s to S3 %s/%s" % ( media_uuid, thumbnail['output_file_fs'], thumbnail['output_file']['s3_bucket'], thumbnail['output_file']['s3_key'] ) } ) )

                s3.upload_file( thumbnail['output_file_fs'], thumbnail['output_file']['s3_bucket'], thumbnail['output_file']['s3_key'] )

        # Store our generic images in S3, and compute various metrics
        # and store the results in a hash to be stored in the database
        # by our caller.
        if output['asset_type'] == 'main':
            images = []
            for filename in sorted( glob.glob( '%s/%s-image-*.jpg' % ( config.transcode_dir, media_uuid ) ) ):
                try:
                    # Calculate the timecode metric.
                    #
                    # FFMPEG for some reason generates a garbage first frame, and
                    # then starts making frames every FPS at FPS/2 in video when
                    # the -vf fps=X option is used (different, crazier behavior
                    # results from usage of -r).
                    sequence = int( re.search( r'image-(\d+).jpg', filename ).groups()[0] )
                    if sequence == 1:
                        continue
                    timecode = ( sequence - 2 ) * ( 1.0 / image_fps )  + ( 1.0 / ( 2 * image_fps ) )
                    image_key = "%s/%s-image-%s.jpg" % ( media_uuid, media_uuid, timecode )
                    
                    blur_score, face_score, rgb_hist = _get_cv_features( filename )
                    
                    cv_metrics = json.dumps( { 'rgb_hist' : json.loads( rgb_hist ) } )

                    # Upload the file
                    s3.upload_file( filename, config.bucket_name, image_key )
                    
                    # Inform the caller abour the metrics.
                    images.append( { 'output_file'    : { 's3_key' : image_key },
                                     'output_file_fs' : filename,
                                     'format'         : 'jpg',
                                     'timecode'       : timecode,
                                     'blur_score'     : blur_score,
                                     'face_score'     : face_score,
                                     'cv_metrics'     : cv_metrics } )
                except Exception as e:
                    # Just proceed on exception.
                    log.error( json.dumps( { 'media_uuid' : media_uuid,
                                             'message' : "ERROR getting features for image %s: %s" % ( filename, e ) } ) )
                    
            output['images'] = images

    return outputs

def generate_thumbnails( media_uuid, input_file_fs, thumbnails, input_frames ):
    '''Takes in a media_uuid, the path to an input movie file, and an
    array of thumbnail data structures.

    Generates the desired thumbnails, and returns a modified
    thumbnails data structure that includes output_file_fs elements
    for each thumbnail.'''

    exif = get_exif( media_uuid, input_file_fs )

    try:
        video_x = int( exif['width'] )
        video_y = int( exif['height'] )
    except Exception as e:
        message = 'Failed to extract width and height from transcoded video for media_uuid %s, terminating.' % ( media_uuid )
        log.error( json.dumps( { 'media_uuid' : media_uuid, 'message' : message } ) )
        raise Exception( message )

    # DEBUG - for the time being we support only the first element of
    # the "times" key of the thumbnails data structure.

    for idx, thumbnail in enumerate( thumbnails ):
        output = ''

        time = thumbnail['times'][0]
        if exif['duration'] is not None and time >= exif['duration']:
            time = float( time ) / 2

        ffmpeg_opts = ' -vframes 1 '
        ffmpeg_scale = ''

        thumbnail_x = None
        thumbnail_y = None

        if thumbnail.get( 'original_size', False ):
            if video_x and video_y:
                thumbnail_x = video_x
                thumbnail_y = video_y
                thumbnail['size'] = "%sx%s" % ( video_x, video_y )
            else:
                log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                           'message' : "Couldn't determine original video size in in order to make an original thumbnail, using 320x240 for the thumbnail size." } ) )
                thumbnail_x = 320
                thumbnail_y = 240
                thumbnail['size'] = "%sx%s" % ( 320, 240 )
        else:
            thumbnail_size = thumbnail.get( 'size', "320x240" )
            thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )
            thumbnail_x = int( thumbnail_x )
            thumbnail_y = int( thumbnail_y )

        thumbnail_aspect_ratio = float( thumbnail_x ) / float( thumbnail_y )

        thumbnail_type = thumbnail.get( 'type', 'static' )

        if video_x and video_y:
            scaled_x = 0
            scaled_y = 0
            scaling_factor = 0
            if video_x < thumbnail_x:
                scaling_factor = float( thumbnail_x ) / video_x
            if video_y < thumbnail_y:
                if float( thumbnail_y ) / video_y > scaling_factor:
                    scaling_factor = float( thumbnail_y ) / video_y
                    
            if scaling_factor > 0:
                scaled_x = int( video_x * scaling_factor ) + 1
                if scaled_x % 2 != 0:
                    scaled_x += 1
                scaled_y = int( video_y * scaling_factor ) + 1
                if scaled_y %2 != 0:
                    scaled_y += 1
            else:
                scaled_x = thumbnail_x
                scaled_y = thumbnail_y

            video_aspect_ratio = video_x / float( video_y )
    
            if video_aspect_ratio > thumbnail_aspect_ratio:
                ffmpeg_scale += ' -vf "scale=trunc(oh*a/2)*2:%s,crop=%s:%s"' % ( scaled_y, thumbnail_x, thumbnail_y )
            else:
                ffmpeg_scale += ' -vf "scale=%s:trunc(ow/a/2)*2,crop=%s:%s"' % ( scaled_x, thumbnail_x, thumbnail_y )
        else:
            ffmpeg_scale += ' -vf scale=%s:%s,crop=%s:%s' % ( thumbnail_x, thumbnail_y, thumbnail_x, thumbnail_y )

        thumbnail_file_fs = config.transcode_dir + "/" + media_uuid + "_%s_%s.%s" % ( thumbnail['label'], idx, thumbnail.get( 'format', 'png' ) )

        if thumbnail_type == 'static':
            cmd = '/usr/local/bin/ffmpeg -y -ss %s -i %s %s %s %s' %( time, input_file_fs, ffmpeg_opts, ffmpeg_scale, thumbnail_file_fs )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'message' : "Running command %s to generate thumbnail for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )

            ( status, output ) = commands.getstatusoutput( cmd )
            output = output.decode( 'utf-8' )

            log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "Thumbnail command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, output ) } ) )

            if status != 0 or not os.path.isfile( thumbnail_file_fs ):
                log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                           'message' : "Failed to generate scaled thumbnail for media_uuid %s, video file %s with command %s" % ( media_uuid, input_file_fs, cmd ) } ) )

                cmd = '/usr/local/bin/ffmpeg -y -ss %s -i %s -vframes 1 -vf scale=%s:%s,crop=%s:%s %s' %( time, input_file_fs, thumbnail_x, thumbnail_y, thumbnail_x, thumbnail_y, thumbnail_file_fs )

                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Running safer command %s to generate thumbnail for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )

                ( status, output ) = commands.getstatusoutput( cmd )
                output = output.decode( 'utf-8' )

                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Thumbnail command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, output ) } ) )

                if status != 0 or not os.path.isfile( thumbnail_file_fs ):
                    log.error( json.dumps( { 'media_uuid' : media_uuid,
                                             'message' : "Failed to generate thumbnail for media_uuid %s, video file %s with command %s, error was ...%s" % ( media_uuid, input_file_fs, cmd, output[-256:] ) } ) )
                    raise Exception( 'Failed to generate thumbnail ...%s' % output[-256:] )
                else:
                    thumbnail['output_file_fs'] = thumbnail_file_fs 
            else:
                thumbnail['output_file_fs'] = thumbnail_file_fs 
        elif thumbnail_type == 'animated':
            #import pdb
            #pdb.set_trace()

            if input_frames is not None:
                frames = float( input_frames[-1] )
                cmd = '/usr/local/bin/ffmpeg -y -i %s' % ( input_file_fs )

                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Running command %s to determine fps for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )

                ( status, cmd_output ) = commands.getstatusoutput( cmd )
                
                fps_string = re.search( r',\s+([\d\.]+)\s+fps', cmd_output )
                
                if fps_string is not None:
                    fps = float( fps_string.groups()[0] )
                else:
                    raise Exception( 'Could not determine fps to generate animated thumbnail.' )

                input_length = float( frames ) / fps 
                output_fps = float( 10 ) / input_length

                cmd = 'cd %s ; /usr/local/bin/ffmpeg -y -i %s %s,fps=%s -f image2 %s-thumb-%%04d.png' % ( config.transcode_dir, input_file_fs, ffmpeg_scale, output_fps, media_uuid )
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Running command %s to create animated gif thumbnails for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )
                ( status, cmd_output ) = commands.getstatusoutput( cmd )
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Animated gif thumbnail generation command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, cmd_output ) } ) )
                
                if status != 0 or not len( [ x for x in os.listdir( config.transcode_dir ) if x.startswith( "%s-thumb-" % media_uuid ) ] ):
                    log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                               'message' : "Failed to generate scaled intermediate images for animated thumbnail, generating unscaled versions." } ) )

                    cmd = 'cd %s ; /usr/local/bin/ffmpeg -y -i %s -vf scale=%s:%s,crop=%s:%s,fps=%s -f image2 %s-thumb-%%04d.png' % ( config.transcode_dir, input_file_fs, thumbnail_x, thumbnail_y, thumbnail_x, thumbnail_y, output_fps, media_uuid )
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'message' : "Running safer command %s to create animated gif thumbnails for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )
                    ( status, cmd_output ) = commands.getstatusoutput( cmd )
                    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                             'message' : "Animated gif thumbnail generation command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, cmd_output ) } ) )
                
                    if status != 0 or not len( [ x for x in os.listdir( config.transcode_dir ) if x.startswith( "%s-thumb-" % media_uuid ) ] ):
                        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                                 'message' : "Failed to generate imtermediate images for animated thumbnail for media_uuid %s, video file %s with command %s, error was ...%s" % ( media_uuid, input_file_fs, cmd, cmd_output[-256:] ) } ) )
                        raise Exception( 'Failed to generate animated thumbnail ...%s' % cmd_output[-256:] )

                cmd = 'cd %s ; /usr/bin/convert -delay 60 -loop 0 %s-thumb-*.png %s' % ( config.transcode_dir, media_uuid, thumbnail_file_fs )
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Running command %s to produce animated gif for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )
                ( status, cmd_output ) = commands.getstatusoutput( cmd )
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Animated gif thumbnail composition command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, cmd_output ) } ) )

                cmd = 'cd %s ; rm %s-thumb-*.png' % ( config.transcode_dir, media_uuid )
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Running command %s to clean up thumbnails for media_uuid %s, video file %s" % ( cmd, media_uuid, input_file_fs ) } ) )
                ( status, cmd_output ) = commands.getstatusoutput( cmd )          
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Animated gif thumbnail removal command output for media_uuid %s, video file %s was: %s" % ( media_uuid, input_file_fs, cmd_output ) } ) )
      
                thumbnail['output_file_fs'] = thumbnail_file_fs 

    return thumbnails

def _get_cv_features( filename ):
    '''Helper function, returns a triple of:
    blur_score, face_score, rgb_hist
    Where blur_score and face_score are floating point numbers, and rgb_hist is JSON'''
    
    cv_bin = os.path.dirname( __file__ ) + '/../../cv/'
    
    blur_cmd = "%s/BlurDetector/blurDetector %s 2> /dev/null" % ( cv_bin, filename )
    ( status, output ) = commands.getstatusoutput( blur_cmd )
    blur_score = float( output )

    rgb_hist_cmd = "%s/ImageDiff/imagediff %s 2> /dev/null" % ( cv_bin, filename )
    ( status, output ) = commands.getstatusoutput( rgb_hist_cmd )
    rgb_hist = output

    face_result = rekog.detect_for_file( filename )
    face_score = 0
    if 'face_detection' in face_result:
        for face in face_result['face_detection']:
            face_score += face['confidence']

    return ( blur_score, face_score, rgb_hist )
        
    
    
    
