import os
import json
import requests
import xmltodict
import time
import iv_config
import iv
import boto
from boto.s3.key import Key

def get_faces(file_data, log, data):
    ifile   = file_data['ifile']
    ofile   = file_data['ofile']
    s3_key  = file_data['key']
    uid     = data['info']['uid']
    uuid    = data['info']['uuid']

    ## Transcode to AVI for Intellivision
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( ifile, ffopts, ofile )
    print( cmd )
    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate AVI file: %s' % cmd )
    ## Copy AVI to S3 and make the URL public
    try:
        s3 = boto.connect_s3(iv_config.awsAccess, iv_config.awsSecret)
        bucket = s3.get_bucket(iv_config.iv_bucket_name)
        bucket_contents = Key(bucket)
        bucket_contents.key = s3_key
        bucket_contents.set_contents_from_filename( ofile )
        bucket_contents.make_public()
    except:
        print 'error copying to S3'
    
    media_url = 'http://s3-us-west-2.amazonaws.com/' + iv_config.iv_bucket_name + '/' + s3_key
    print media_url
    session_info = iv.open_session()
    user_id = iv.login(session_info, uid)
    response = iv.analyze(session_info, user_id, media_url)
    file_id = response['file_id']
    wait_time = response['wait_time']
    time.sleep(wait_time)
    tracks = iv.retrieve(session_info, user_id, file_id, uuid)
    for i,track in enumerate(tracks.findAll('track')):
        track_id = i
        person_id = int(track.personid.string)
        detection_score = int(track.detectionscore.string)
        if ((detection_score > iv_config.minimum_detection_score) & (person_id < 0)):
            person_id = iv.add_person(session_info, uid)
            iv.train_person(session_info, user_id, person_id, track_id, file_id, media_url)
            track.personid.string = str(person_id)
    print 'Track number = ' + str(track_id)
    print 'person_id = ' + str(person_id)
    print 'detectionscore = ' + track.detectionscore.text
    print 'Recognition confidence = ' + track.recognitionconfidence.text
    print track.bestfaceframe.text
    tracks_string = str(tracks)
    tracks_dict = xmltodict.parse(tracks_string)
    tracks_json = json.dumps(tracks_dict)
    return(tracks_json)
    iv.logout(session_info, user_id)
    iv.close_session(session_info)
    faces_data = {'file_id': file_id}
    return (faces_data)

def transcode_main( file_data, log, data, files=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']
    rotation = data['exif']['rotation']
    mimetype = data['mimetype']

    ffopts = ' -c:a libfdk_aac '
    if rotation == '0' and mimetype == 'video/mp4':
        log.debug( 'Video is non-rotated mp4, leaving it alone.' )
        data['mimetype'] = 'video/mp4'
        return
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

def transcode_avi( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']

    # Also generate AVI for IntelliVision (temporary)
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -v 0 -y -i %s %s %s' % ( ifile, ffopts, ofile )

    print( cmd )
    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate AVI file: %s' % cmd )

def move_atom( file_data, log, data=None ):
    '''Attempt to relocate the atom, if there is a problem do not
    terminate execution.'''
    ifile = file_data['ifile']
    ofile = file_data['ofile']

    cmd = '/usr/local/bin/qtfaststart %s' % ofile
    log.info( cmd )
    if os.system( cmd ) != 0:
        log.error( 'Failed to run qtfaststart on the output file' )
        
def generate_poster( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    rotation = data['exif']['rotation']
    width    = data['exif']['width']
    height   = data['exif']['height']

    if height == 0: 
        aspect_ratio = 4/float(3)
    else:
        aspect_ratio = width/float(height)
    log.info( 'Poster aspect ratio is ' + str( aspect_ratio ) )
    
    cmd = ''

    if rotation == '90' or rotation == '270' or aspect_ratio < 16/float(9):
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 0.5 -i %s -vframes 1 -vf scale=-1:180,pad=320:180:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 0.5 -i %s -vframes 1 -vf scale=320:-1,pad=320:180:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing poster generation command: '+ cmd )

    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate poster with command: %s' % cmd )
        
def generate_thumbnail( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    rotation = data['exif']['rotation']
    width    = data['exif']['width']
    height   = data['exif']['height']    

    cmd = ''

    if rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 0.5 -i %s -vframes 1 -vf scale=-1:128,pad=128:128:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -v 0 -y -ss 0.5 -i %s -vframes 1 -vf scale=128:-1,pad=128:128:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing thumbnail generation command: ' + cmd )

    if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate thumbnail with command: %s' % cmd )

def generate_face( file_data, log, data=None, skip=False ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    data['found_faces'] = False

    if not skip:
        cmd = 'python /viblio/bin/extract_face.py %s %s' % ( ifile, ofile )
        log.info( 'Executing face generation command: ' + cmd )
        if os.system( cmd ) != 0 or not os.path.isfile( ofile ):
            log.warning( 'Failed to find any faces in video %s for command: %s' % ( ifile, cmd ) )
        else:
            data['found_faces'] = True
