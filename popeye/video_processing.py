import json
#import logging
import os

#from appconfig import AppConfig
#config = AppConfig( 'popeye' ).config()
#logging.basicConfig( filename = config['logfile'], level = config.loglevel )
#log = logging.getLogger( __name__ )

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

    return( { 'file_ext'    : file_ext, 
              'mime_type'   : mime_type, 
              'lat'         : lat, 
              'lng'         : lng, 
              'create_date' : create_date, 
              'rotation'    : rotation, 
              'frame_rate'  : frame_rate
              } )

def get_faces(avi_video):
    basename, ext = os.path.splitext( avi_video )
    media_uuid = os.path.split( basename )[1]
    media_url = 'http://s3-us-west-2.amazonaws.com/viblio-uploaded-files/' + media_uuid + '/' + media_uuid + ext
    print media_url
    print basename
    session_info = iv.open_session()
    user_id = iv.login(session_info, iv_config.uid)
    file_id = iv.analyze(session_info, user_id, media_url)
    print file_id
    x = iv.retrieve(session_info, user_id, file_id, basename)
    iv.logout(session_info, user_id)
    iv.close_session(session_info)
    return (x)

def transcode(c, mimetype, rotation):
    ffopts = ''
    if rotation == '0' and mimetype == 'video/mp4':
        print( 'Video is non-rotated mp4, leaving it alone.' )
        c['video']['output'] = c['video']['input']
    else:
        if rotation == '90':
            print( 'Video is rotated 90 degrees, rotating.' )
            ffopts += ' -vf transpose=1 -metadata:s:v:0 rotate=0 '
        elif rotation == '180':
            print( 'Video is rotated 180 degrees, rotating.' )
            ffopts += ' -vf hflip,vflip -metadata:s:v:0 rotate=0 '
        elif rotation == '270':
            print( 'Video is rotated 270 degrees, rotating.' )
            ffopts += ' -vf transpose=2 -metadata:s:v:0 rotate=0 '

    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( c['video']['input'], ffopts, c['video']['output'] )
    print( cmd )
    if not os.system( cmd ) == 0:
        print( 'Failed to execute: %s' % cmd )
        return
    mimetype = 'video/mp4'

    # Also generate AVI for IntelliVision (temporary)
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( c['video']['output'], ffopts, c['avi']['output'] )
    print( cmd )
    if not os.system( cmd ) == 0:
        print( 'Failed to generate AVI file: %s' % cmd )
        return 
    # Move the metadata atom(s) to the front of the file.  -movflags faststart is
    # not a valid option in our version of ffmpeg, so cannot do it there.  qt-faststart
    # is broken.  qtfaststart is a python based solution that has worked much better for me
    cmd = '/usr/local/bin/qtfaststart %s' % c['video']['output']
    print( cmd )
    if not os.system( cmd ) == 0:
        print( 'Failed to run qtfaststart on the output file' )
        
def generate_poster(input_video, output_jpg, rotation):
    if rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=320:-1,pad=320:240:0:oh/2-ih/2 %s' %(input_video, output_jpg)
        print cmd
        if not os.system( cmd ) == 0:
            print 'Failed to execute: %s' % cmd
    elif rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:240,pad=320:240:ow/2-iw/2:0 %s' %(input_video, output_jpg)
        print cmd
        if not os.system( cmd ) == 0:
            print 'Failed to execute: %s' % cmd
        
def generate_thumbnail(input_video, output_jpg, rotation):
    if rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=128:-1,pad=128:128:0:oh/2-ih/2 %s' %(input_video, output_jpg)
        print cmd
        if not os.system( cmd ) == 0:
            print 'Failed to execute: %s' % cmd
    elif rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:128,pad=128:128:ow/2-iw/2:0 %s' %(input_video, output_jpg)
        print cmd
        if not os.system( cmd ) == 0:
            print 'Failed to execute: %s' % cmd