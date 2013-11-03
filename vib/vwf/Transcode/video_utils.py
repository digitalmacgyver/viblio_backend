import commands
import os
import json

log = logging.getLogger( __name__ )

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

def transcode_main( file_data, log, data, files=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']
    rotation = data['exif']['rotation']
    mimetype = data['mimetype']

    ffopts = ' -c:a libfdk_aac -b:v 1500k '

    if rotation == '90':
        log.info( 'Video is rotated 90 degrees, rotating.' )
        ffopts += ' -vf transpose=1 -metadata:s:v:0 rotate=0 '
    elif rotation == '180':
        log.info( 'Video is rotated 180 degrees, rotating.' )
        ffopts += ' -vf hflip,vflip -metadata:s:v:0 rotate=0 '
    elif rotation == '270':
        log.info( 'Video is rotated 270 degrees, rotating.' )
        ffopts += ' -vf transpose=2 -metadata:s:v:0 rotate=0 '

    cmd = '/usr/local/bin/ffmpeg -y -i %s %s %s' % ( ifile, ffopts, ofile )
    log.info( cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate transcoded video with: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )

    data['mimetype'] = 'video/mp4'

def move_atom( file_data, log, data=None ):
    '''Attempt to relocate the atom, if there is a problem do not
    terminate execution.'''
    ifile = file_data['ifile']
    ofile = file_data['ofile']

    cmd = '/usr/local/bin/qtfaststart %s' % ofile
    log.info( cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        log.warning( 'Failed to run qtfaststart on the output file' )
    else:
        log.debug( 'qtfaststart command returned successful completion status.' )        

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

