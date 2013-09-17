import json
import worker
import os
import iv_config
import iv

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
    if os.system( cmd ) != 0 or not os.path.isfile( c['video']['output'] ):
        print( 'Failed to generate transcoded video with: %s' % cmd )
        raise Exception( 'Failed to generate transcoded video with: %s' % cmd )
    mimetype = 'video/mp4'

    # Also generate AVI for IntelliVision (temporary)
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( c['video']['output'], ffopts, c['avi']['output'] )
    print( cmd )
    if os.system( cmd ) != 0 or not os.path.isfile( c['avi']['output'] ):
        print( 'Failed to generate AVI file: %s' % cmd )
        raise Exception( 'Failed to generate AVI file: %s' % cmd )

    # Move the metadata atom(s) to the front of the file.  -movflags
    # faststart is not a valid option in our version of ffmpeg, so
    # cannot do it there.  qt-faststart is broken.  qtfaststart is a
    # python based solution that has worked much better for me
    cmd = '/usr/local/bin/qtfaststart %s' % c['video']['output']
    print( cmd )
    if os.system( cmd ) != 0:
        print( 'Failed to run qtfaststart on the output file' )
        
def generate_poster(input_video, output_jpg, rotation, width, height):
    if height == 0: 
        aspect_ratio = 4/float(3)
    else:
        aspect_ratio = width/float(height)
    print 'aspect ratio is', aspect_ratio
    
    cmd = ''

    if rotation == '90' or rotation == '270' or aspect_ratio < 16/float(9):
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:180,pad=320:180:ow/2-iw/2:0 %s' %(input_video, output_jpg)
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=320:-1,pad=320:180:0:oh/2-ih/2 %s' %(input_video, output_jpg)
        
    print cmd
    if os.system( cmd ) != 0 or not os.path.isfile( output_jpg ):
        print 'Failed to generate poster with command: %s' % cmd

def generate_thumbnail(input_video, output_jpg, rotation, width, height):
    cmd = ''

    if rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:128,pad=128:128:ow/2-iw/2:0 %s' %(input_video, output_jpg)
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=128:-1,pad=128:128:0:oh/2-ih/2 %s' %(input_video, output_jpg)

    if os.system( cmd ) != 0 or not os.path.isfile( output_jpg ):
        print 'Failed to generate thumbnail with command: %s' % cmd
