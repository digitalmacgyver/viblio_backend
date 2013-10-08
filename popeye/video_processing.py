import commands
import os
import json
import requests
import xmltodict
import time
import iv_config
import iv
import boto
import sys
from boto.s3.key import Key
from bs4 import BeautifulSoup, Tag

# Our application config
from appconfig import AppConfig
try:
    config = AppConfig( 'popeye' ).config()
except Exception, e:
    print( str(e) )
    sys.exit(1)

def get_faces(file_data, log, data):
    s3_key  = file_data['key']
    uid     = data['info']['uid']
    media_uuid = os.path.split(s3_key)[0]
    minimum_detection_score = iv_config.minimum_detection_score
    minimum_recognition_score = iv_config.minimum_recognition_score
    ## Make S3 URL public for IntelliVision
    try:
        s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
        bucket = s3.get_bucket(config.bucket_name)
        bucket_contents = Key(bucket)
        bucket_contents.key = s3_key
        original_acl = bucket_contents.get_acl()
        bucket_contents.make_public()
    except:
        log.error(  'Error making S3 URL public' ) 
        raise Exception( "Error making S3 URL public" )
    media_url = 'http://s3-us-west-2.amazonaws.com/' + config.bucket_name + '/' + s3_key
    log.info( media_url )
    # Open session and login user for IntelliVision
    session_info = iv.open_session()
    user_id = iv.login(session_info, uid )
    # Send the video for processing by IntelliVision
    # Since analyze may need to restart session, session info is returned
    response = iv.analyze(session_info, user_id, uid, media_url)
    session_info = {'key': response['key'], 
                    'secret': response['secret']}
    user_id = response['user_id']
    file_id = response['file_id']
    # in case wait_time is absent, wait for fixed time
    if response.get( 'wait_time' ):
        wait_time = response['wait_time']
        time.sleep(wait_time)
    else:
        log.info(log, 'waiting for 120 seconds')
        time.sleep(120)
    # Get Face Recognition results from IntelliVision
    tracks = iv.retrieve(session_info, user_id, file_id)
    if tracks == 'No Tracks':
        log.info (log, 'No tracks found')
        return json.dumps( {"tracks": {"file_id": file_id, "numberoftracks": "0"}} )
    number_of_tracks = int( tracks.numberoftracks.string )
    # Create a new Tracks data structure starting with file_id & numberftracks
    file_id_tag = Tag (name="file_id")
    file_id_tag.string = file_id
    tracks_tag = Tag (name = "tracks")
    tracks_tag.insert(0, tracks.numberoftracks)
    tracks_tag.insert(0, file_id_tag)
    log.debug( str(tracks_tag) )
    # Process each track, one at a time
    for i,track in enumerate(tracks.findAll('track')):
        track_id = track.trackid.string
        formatted_track_id = '%02d' %int(track_id)
        person_id = track.personid.string
        detection_score = float(track.detectionscore.string)
        if ( person_id == '-1' ):
            # unknown person
            if ( detection_score > minimum_detection_score ):
                # Train unknown person if detection score is high enough
                new_person_id = iv.add_person(session_info, user_id)
                track.personid.string = new_person_id
                formatted_new_person_id = '%02d' %int(new_person_id)
                log.info( 'Added a new person: ' + new_person_id )
                log.info( "downloading with best face frame" )
                url = track.bestfaceframe.string
                r = requests.get(url)
                filename = '/mnt/uploaded_files/' + media_uuid + '_face_' + formatted_track_id + '_' + formatted_new_person_id + '.jpg'
                with open(filename, "wb") as f:
                    f.write(r.content)
                face_key = media_uuid + '/' + media_uuid + '_face_' + formatted_track_id + '_' + formatted_new_person_id + '.jpg'
                log.info( "Uploading face to S3" )
                try:
                    bucket_contents.key = face_key
                    bucket_contents.set_contents_from_filename(filename)
                    cmd = 'rm %s' % ( filename )
                    log.info( cmd )
                    ( status, output ) = commands.getstatusoutput( cmd )
                    log.debug( 'Command output was: ' + output )
                except:
                    log.error( 'Upload to S3 failed' )
                    raise( 'Upload to S3 of %s failed' % ( face_key ) )
                try:
                    iv.train_person(session_info, user_id, new_person_id, track_id, file_id, media_url)
                    log.info( 'training: ' + new_person_id )
                except:
                    log.warning( 'Failed to train unknown person' )
                # update bestfaceframe and insert track into output
                track.bestfaceframe.string = face_key
                tracks_tag.append(track)
                log.debug(log, str(tracks_tag))
            else:
                # Unknown person with low detection score
                track.personid.string = ''
                track.bestfaceframe.string = ''    
                number_of_tracks -= 1
                log.debug(log, str(tracks_tag))
        else:
            # Known person
            recognition_score = float(track.recognitionconfidence.string)
            if ( recognition_score > minimum_recognition_score ):
                # Train known person only if recognition score was high enough
                try:
                    log.info( 'training: ' + person_id )
                    iv.train_person(session_info, user_id, str(person_id), track_id, file_id, media_url)
                except:
                    log.info( 'Failed to train known person' )
            formatted_person_id = '%02d' %int(person_id)            
            url = track.bestfaceframe.string
            r = requests.get(url)
            filename = '/mnt/uploaded_files/' + media_uuid + '_face_' + formatted_track_id + '_' + formatted_person_id + '.jpg'
            with open(filename, "wb") as f:
                f.write(r.content)
            face_key = media_uuid + '/' + media_uuid + '_face_' + formatted_track_id + '_' + formatted_person_id + '.jpg'
            log.info( "Uploading face to S3" )
            try:
                bucket_contents.key = face_key
                bucket_contents.set_contents_from_filename(filename)
            except:
                log.info( 'Upload to S3 of %s failed' % ( filename ) )
                raise Exception( 'Upload to S3 of %s failed' % ( filename ) )
            # update bestfaceframe and append track to output
            track.bestfaceframe.string = face_key
            tracks_tag.append(track)
            log.debug(log, str(tracks_tag))
    tracks_tag.numberoftracks.string = str(number_of_tracks)
    tracks_string = str(tracks_tag)
    tracks_dict = xmltodict.parse(tracks_string)
    tracks_json = json.dumps(tracks_dict)
    log.info(log, str(tracks_json))
    # Cleanup permissions, logout & close session
    bucket_contents.set_acl(original_acl)
    iv.logout(session_info, user_id)
    iv.close_session(session_info)
    return tracks_json

def transcode_main( file_data, log, data, files=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']
    rotation = data['exif']['rotation']
    mimetype = data['mimetype']

    ffopts = ' -c:a libfdk_aac '
    if rotation == '0' and mimetype == 'video/mp4':
        log.debug( 'Video is non-rotated mp4, renaming it.' )
        try:
            os.rename( ifile, ofile )
        except Exception as e:
            log.error( "Failed to rename %s to %s" % ( src, tar ) )
            raise
        data['mimetype'] = 'video/mp4'
        return
    else:
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

def transcode_avi( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']

    # Also generate AVI for IntelliVision (temporary)
    ffopts = ''
    cmd = '/usr/local/bin/ffmpeg -y -i %s %s %s' % ( ifile, ffopts, ofile )

    log.info( cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate AVI file: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )

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
        log.error( 'Failed to run qtfaststart on the output file' )
    else:
        log.debug( 'qtfaststart command returned successful completion status.' )        

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
        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=-1:180,pad=320:180:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=320:-1,pad=320:180:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing poster generation command: '+ cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate poster with command: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )        
        
def generate_thumbnail( file_data, log, data=None ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    rotation = data['exif']['rotation']
    width    = data['exif']['width']
    height   = data['exif']['height']    

    cmd = ''

    if rotation == '90' or rotation == '270':
        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=-1:128,pad=128:128:ow/2-iw/2:0 %s' %( ifile, ofile )
    elif rotation == '0' or rotation == '180':
        cmd = '/usr/local/bin/ffmpeg -y -ss 0.5 -i %s -vframes 1 -vf scale=128:-1,pad=128:128:0:oh/2-ih/2 %s' %( ifile, ofile )

    log.info( 'Executing thumbnail generation command: ' + cmd )
    ( status, output ) = commands.getstatusoutput( cmd )
    log.debug( 'Command output was: ' + output )
    if status != 0 or not os.path.isfile( ofile ):
        raise Exception( 'Failed to generate thumbnail with command: %s' % cmd )
    else:
        log.debug( 'ffmpeg command returned successful completion status.' )

def generate_face( file_data, log, data=None, skip=False ):
    ifile = file_data['ifile']
    ofile = file_data['ofile']    
    data['found_faces'] = False

    if not skip:
        cmd = 'python /viblio/bin/extract_face.py %s %s' % ( ifile, ofile )
        log.info( 'Executing face generation command: ' + cmd )
        ( status, output ) = commands.getstatusoutput( cmd )
        log.debug( 'Command output was: ' + output )
        if status != 0 or not os.path.isfile( ofile ):
            log.warning( 'Failed to find any faces in video %s for command: %s' % ( ifile, cmd ) )
        else:
            log.debug( 'extract_face command returned successful completion status.' )
            data['found_faces'] = True
