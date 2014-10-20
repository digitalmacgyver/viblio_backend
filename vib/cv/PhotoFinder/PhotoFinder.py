import boto.sqs.connection
from boto.sqs.message import RawMessage
import commands
import glob
import json
import logging
from logging import handlers
import os
import re
from sqlalchemy import and_
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *
from vib.utils.s3 import check_exists, download_file, upload_file
import vib.vwf.Transcode.transcode_utils

log = logging.getLogger( 'vib.cv.PhotoFinder' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'PhotoFinder: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def find_photos( media_uuid,
                 video_file        = None, # Will be downloaded if not provided.
                 start_time        = 0,
                 end_time          = None, # Defaults to duration, negative values are taken as offsets from end.
                 images_per_second = None,
                 faces_only        = False ):
    '''Find photos in a given media file, store them in S3, and associate
    them with the media file in the database.

    If video_file is provided it is taken to be the filesystem path to
    the video asset for media_uuid that we wish to find photos in.
    
    If it is not provided the 'original' video asset is found and
    operated on.

    Only the portion of the video from start_time to end_time is
    considered, which default to the entire video.

    Negative start and end_time values are taken as offsets from the
    end of the video.
    
    By default between 4 and 30 images are found at evenly spaced
    intervals between start and end time while trying to take an image
    every 5 seconds.  This can be overriden by explicitly setting the
    image_per_second option.

    If faces_only is set to true, only those images which include a
    face will be retained.

    Returns an array of:
    { media_asset_uuid : "ABCD",
      timecode : 2.5,
      blur_score : 0.5,
      face_score : 0.8,
      cv_metrics : "blah blah blah" }
    Data structures for the image media_assets that were found and stored.

    '''
    
    orm = vib.db.orm.get_session()

    media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

    media_asset = None
    image_dir = "%s/%s/find_photos/" % ( config.faces_dir, media_uuid )
    if not os.path.isdir( image_dir ):
        os.makedirs( image_dir )

    cleanup_video_file = False
    if video_file is None:
        media_assets = orm.query( MediaAssets ).filter( and_( MediaAssets.asset_type == 'original', MediaAssets.media_id == media.id ) )[:]
        media_asset = None
        if len( media_asset ) != 1:
            # Handle the case where there is no 'original' video.
            media_asset = orm.query( MediaAssets ).filter( and_( MediaAssets.asset_type == 'main', MediaAssets.media_id == media.id ) ).one()
        else:
            media_asset = media_assets[0]
        video_file = "%s/%s/find_photos/video_%s" % ( config.faces_dir, media_uuid, media_uuid )
        download_file( video_file, config.bucket_name, media_asset.uri )

        if not os.path.isfile( video_file ):
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message'    : "Error: could not get video file for media_uuid: %s" % ( media_uuid ) } ) )
            raise Exception( "Error: could not get video file for media_uuid: %s" % ( media_uuid ) )
        cleanup_video_file = True
    elif not os.path.isfile( video_file ):
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'message'    : "Error: no video file found at path: %s" % ( video_file ) } ) )
        raise Exception( "Error: no video file found at path: %s" % ( video_file ) )
        
    exif = vib.vwf.Transcode.transcode_utils.get_exif( media_uuid, video_file )
    
    video_duration = exif['duration']

    if video_duration is None:
        log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                   'message'    : "Warning: could not determine duration for video, negative end times disabled." } ) )

    if start_time < 0:
        start_time = video_duration + start_time
    
    start_time = max( float( start_time ), 0 )

    #import pdb
    #pdb.set_trace()

    if video_duration is not None:
        if end_time is None:
            end_time = video_duration
        elif end_time < 0:
            end_time = video_duration + end_time

        end_time = min( end_time, video_duration )
    else:
        if end_time < 0:
            end_time = None

    if end_time is not None and end_time < start_time:
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'message'    : "Error: end_time (%s) must be greater than start_time (%s)" % ( end_time, start_time ) } ) )
        raise Exception( "Error: end_time (%s) must be greater than start_time (%s)" % ( end_time, start_time ) )

    duration = None
    if end_time is not None:
        duration = end_time - start_time

    image_fps = None
    if images_per_second is None:
        image_fps = 0.2
        if duration and duration < 20:
            image_fps = 4.0 / duration
        elif duration and duration > 150:
            image_fps = 30.0 / duration
    else:
        image_fps = images_per_second
        
    rotation = exif['rotation']

    image_opts = ''

    if rotation == '90':
        image_opts += ' -metadata:s:v:0 rotate=0 -vf transpose=1,'
    elif rotation == '180':
        image_opts += ' -metadata:s:v:0 rotate=0 -vf hflip,vflip,'
    elif rotation == '270':
        image_opts += ' -metadata:s:v:0 rotate=0 -vf transpose=2,'
    else:
        image_opts += ' -vf '

    image_opts += 'fps=%s ' % ( image_fps )

    to_clause = ""
    if end_time is not None:
        to_clause = ' -t %f ' % ( end_time )

    output_cmd = image_opts + ' -qscale:v 2 %s %s/%s-image-%%04d.jpg' % ( to_clause, image_dir, media_uuid )

    cmd = '/usr/local/bin/ffmpeg -y -ss %f -i %s %s' % ( start_time, video_file, output_cmd )
    log.info( json.dumps( { 'media_uuid' : media_uuid,
                            'message' : "Running FFMPEG command %s" % cmd } ) )
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    cmd_output = cmd_output.decode( 'utf-8' )

    log.debug( json.dumps( { 'media_uuid' : media_uuid,
                             'message' : "FFMPEG command output was: %s" % cmd_output } ) )

    if status != 0:
        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                 'message' : 'Failed to generate images from video with: %s, error was ...%s' % ( cmd, cmd_output[-256:]) } ) )
        raise Exception( 'Failed to generate images from video: ...%s' % cmd_output[-256:] )

    
    results = []
    for filename in sorted( glob.glob( '%s/%s-image-*.jpg' % ( image_dir, media_uuid ) ) ):
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
            timecode = start_time + ( sequence - 2 ) * ( 1.0 / image_fps )  + ( 1.0 / ( 2 * image_fps ) )
            image_key = "%s/%s-image-%s.jpg" % ( media_uuid, media_uuid, timecode )
                    
            if check_exists( config.bucket_name, image_key ) is not None:
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Ignoring image that is already present, and deleting temporary file %s for media %s" % ( filename, media_uuid ) } ) )
                os.remove( filename )
                continue

            blur_score, face_score, rgb_hist = vib.vwf.Transcode.transcode_utils._get_cv_features( filename )
                    
            if faces_only and face_score < 0.8:
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Deleting temporary file %s for media %s" % ( filename, media_uuid ) } ) )
                os.remove( filename )
                continue

            cv_metrics = json.dumps( { 'rgb_hist' : json.loads( rgb_hist ) } )

            # Upload the file
            upload_file( filename, config.bucket_name, image_key )

            image_uuid = str( uuid.uuid4() )

            log.info( json.dumps( {
                'media_uuid' : media_uuid,
                'asset_type' : 'image',
                'output_uuid' : image_uuid,
                'message' : "Creating image database row of uuid %s for media %s of asset_type %s and uri %s" % ( image_uuid, media_uuid, 'image', image_key ) } ) )

            image_asset = MediaAssets( uuid       = image_uuid,
                                       asset_type = 'image',
                                       mimetype   = 'image/jpeg',
                                       bytes      = os.path.getsize( filename ),
                                       uri        = image_key,
                                       location   = 'us',
                                       timecode   = timecode,
                                       blur_score = blur_score,
                                       face_score = face_score,
                                       cv_metrics = cv_metrics,
                                       view_count = 0 )
            media.assets.append( image_asset )
            orm.commit()

            results.append( {
                'media_asset_uuid' : image_uuid,
                'timecode'         : timecode,
                'blur_score'       : blur_score,
                'face_score'       : face_score,
                'cv_metrics'       : cv_metrics } )

            log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "Deleting temporary file %s for media %s" % ( filename, media_uuid ) } ) )
            os.remove( filename )

        except Exception as e:
            # Just proceed on exception.
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "ERROR storing image %s: %s" % ( filename, e ) } ) )

    if cleanup_video_file:
        try:
            os.remove( video_file )
        except Exception as e:
            # Just proceed on exception.
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "ERROR removing video file %s: %s" % ( video_file, e ) } ) )

    return results


def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

def run():
    try:
        sqs = __get_sqs().get_queue( config.photo_finder_queue )
        sqs.set_message_class( RawMessage )

        message = None
        message = sqs.read( wait_time_seconds = 20 )

        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()

        try:
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body %s: " % body } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % e } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % options } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %s" % e } ) )
        
        # We do best effort here, delete the message so another worker
        # doesn't start processing it.
        sqs.delete_message( message )   
        message = None

        media_uuid        = options['media_uuid']
        video_file        = options.get( 'video_file', None )

        start_time        = options.get( 'start_time', 0 )
        if start_time is not None:
            start_time = float( start_time )

        end_time          = options.get( 'end_time', None )
        if end_time is not None:
            end_time = float( end_time )

        images_per_second = options.get( 'images_per_second', None )
        if images_per_second is not None:
            images_per_second = float( images_per_second )

        faces_only        = options.get( 'faces_only', False )

        results = find_photos( media_uuid        = media_uuid,
                               video_file        = video_file,
                               start_time        = start_time,
                               end_time          = end_time,
                               images_per_second = images_per_second,
                               faces_only        = faces_only )
                     
        return True

    except Exception as e:
        log.info( json.dumps( { 'message'   : 'Failed to find photos, error was: %s' % ( e ) } ) )
        raise
    finally:
        if message != None:
            # Even if something went wrong, make sure we delete the
            # message so we don't end up stuck in an infinite loop
            # trying to process this message.
            sqs.delete_message( message )   

