import json
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

def transcode_main( ifile, ofile, log, data, files=None ):
    rotation = data['exif']['rotation']
    mimetype = data['mimetype']

    ffopts = ''
    if rotation == '0' and mimetype == 'video/mp4':
        log.info( 'Video is non-rotated mp4, leaving it alone.' )
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

    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( ifile, ffopts, ofile )
    log.info( cmd )
    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate transcoded video with: %s' % cmd )

    data['mimetype'] = 'video/mp4'

def transcode_avi( ifile, ofile, log, data, files=None ):
    # Also generate AVI for IntelliVision (temporary)
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( ifile, ffopts, ofile )
    print( cmd )
    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate AVI file: %s' % cmd )

def move_atom( ifile, ofile, log, data, files=None ):
    '''Attempt to relocate the atom, if there is a problem do not
    terminate execution.'''
    cmd = '/usr/local/bin/qtfaststart %s' % ofile
    print( cmd )
    if os.system( cmd ) != 0:
        log.error( 'Failed to run qtfaststart on the output file' )
        
def generate_poster( ifile, ofile, log, data, files=None ):
    rotation = data['exif']['rotation']
    width    = data['exif']['width']
    height   = data['exif']['height']

    if height == 0: 
        aspect_ratio = 4/float(3)
    else:
        aspect_ratio = width/float(height)
    log.info( 'Poster aspect ratio is ' + aspect_ratio )
    
    cmd = ''

    if rotation == '90' or rotation == '270' or aspect_ratio < 16/float(9):
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:180,pad=320:180:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=320:-1,pad=320:180:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing poster generation command: '+ cmd )

    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate poster with command: %s' % cmd )
        
def generate_thumbnail( ifile, ofile, log, data, files=None ):
    rotation = data['exif']['rotation']
    width    = data['exif']['width']
    height   = data['exif']['height']    

    cmd = ''

    if rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=-1:128,pad=128:128:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 1 -i %s -vframes 1 -vf scale=128:-1,pad=128:128:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing thumbnail generation command: ' + cmd )

    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate thumbnail with command: %s' % cmd )

def generate_face( ifile, ofile, log, data, skip = False ):
    data['found_faces'] = False

    if not skip:
        cmd = 'python /viblio/bin/extract_face.py %s %s' % ( ifile, ofile )
        log.info( 'Executing face generation command: ' + cmd )
        if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
            log.warning( 'Failed to find any faces in video %s for command: %s' % ( ifile, cmd ) )
        else:
            data['found_faces'] = True
