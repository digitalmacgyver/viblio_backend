#!/usr/bin/env python

'''
Install a cron job to run call_build_smiling_faces.py once an hour or
so.

Package / push to staging.
'''

import boto.swf.layer2 as swf
import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
import commands
import datetime
import json
import hashlib
import logging
from logging import handlers
import math
import os
import random
import shutil
from sqlalchemy import and_
import time
import uuid

import vib.db.orm
from vib.db.models import *
from vib.utils.s3 import download_string, download_file, upload_file
from vib.vwf.Transcode.transcode_utils import get_exif

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'build_smiling_faces: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def generate_clips( user_uuid, 
                    workdir,
                    min_clip_secs       = 2.5,
                    max_clip_secs       = 5,
                    max_input_videos    = 120,
                    max_secs_per_input  = 9,
                    max_clips_per_input = 3,
                    min_output_secs     = 6,
                    max_output_secs     = 120,
                    output_x            = 640,
                    output_y            = 360 ):
    '''Takes the input parameters:
    user_uuid, 
    workdir             = Temporary directory to store videos and clips
    min_clip_secs       = Default 2.5. No clips shorter than this will be included
    max_clip_secs       = Default 5. No clips longer than this will be included
    max_input_videos    = Default 120. At most this many videos with faces will be considered
    max_secs_per_input  = Default 9. Once this threshold is reached, no
                          more clips will be added from this input
    max_clips_per_input = Default 3. At most this many clips will be included per input
    min_output_secs     = Default 6. If this threshold is not reached, return false
    max_output_secs     = Default 120.  One this threshold is reached, no more clips will 
                          be added
    output_x            = Default 640. The output video width in pixels
    output_y            = Default 360. The output video height in pixels
                          
    NOTE: If max_clip_secs*max_clips_per_input != max_secs_per_input
    then the lesser of the two will determine when we stop including
    clips from a video.
    '''
    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                            'message'   : 'Getting user id for user_uuid %s' % ( user_uuid ) } ) )

    # Get the list of movies for the current user.
    orm = vib.db.orm.get_session()
    orm.commit()

    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                            'message'   : 'Getting media_files for user_id %s' % ( user.id ) } ) )
    
    media_files = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.status == 'complete', Media.is_viblio_created == False ) ).order_by( Media.recording_date )[:]

    orm.close()

    cut_lines = []

    output_secs = 0
    output_clips = 0

    for media in media_files:
        media_uuid = media.uuid

        if output_secs >= max_output_secs:
            log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                    'message'   : 'max_output_secs limit reached, skipping analysis of media_uuid: %s' % ( media_uuid ) } ) )
            break
        
        if output_clips >= max_input_videos:
            log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                    'message'   : 'max_input_videos limit reached, skipping analysis of media_uuid: %s' % ( media_uuid ) } ) )
            break

        try:
            # Where various things are located.
            visibility_key = '%s/%s_recognition_input.json' % ( media_uuid, media_uuid )

            # If there is a valid data structure for us to see faces in this video.
            #
            # NOTE: Many videos will not have this data strucure, that
            # is fine, just skip those.
            try: 
                tracks = json.loads( download_string( config.bucket_name, visibility_key ) )['tracks']
                g = open( "%s/%s_tracks.json" % ( workdir, media_uuid ), 'w' )
                json.dump( tracks, g )
                g.close()
                log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                        'message'   : 'Downloaded tracks for media_uuid: %s' % ( media_uuid ) } ) )
            except Exception as e:
                log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                        'message'   : "Couldn't download tracks for media_uuid: %s, skipping." % ( media_uuid ) } ) )
                continue

            input_secs = 0
            input_clips = 0
            cuts = [ ]

            for track in tracks:
                # Stop working on this input if we've got all we need from it.
                if input_secs >= max_secs_per_input:
                    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                            'message'   : 'max_secs_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                    break
                if input_clips >= max_clips_per_input:
                    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                            'message'   : 'max_clips_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                    break

                # Skip tracks where the person isn't happy.
                if not track['faces'][0]['isHappy']:
                    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                            'message'   : 'Skipping track where person is not happy for media_uuid: %s' % ( media_uuid ) } ) )
                    continue

                track_cuts = [ ]

                for vi in track['visiblity_info']:
                    # Stop working on this input if we've got all we need from it.
                    if input_secs >= max_secs_per_input:
                        log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                                'message'   : 'max_secs_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                        break
                    if input_clips >= max_clips_per_input:
                        log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                                'message'   : 'max_clips_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                        break


                    start = float( vi['start_frame'] )/1000
                    end = float( vi['end_frame'] )/1000

                    # Skip clips that are too short.
                    if end - start < min_clip_secs:
                        log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                                 'message'   : 'Skipping cut %s-%s because it is shorter than min_clip_secs' % ( start, end ) } ) )
                        continue

                    # Trim clips that are too long.
                    if end - start > max_clip_secs:
                        log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                                 'message'   : 'Trimming cut %s-%s to end at %s because it is longer than max_clip_secs' % ( start, end, start+max_clip_secs ) } ) )
                        end = start + max_clip_secs

                    # Add the clip to our list of clips
                    track_cuts.append( [ start, end ] )

                    # Update our tracking stats
                    output_secs += end - start
                    output_clips += 1
                    input_secs += end - start
                    input_clips += 1
                
                # If the current input had any cuts we wanted, add it to the master list.
                if len( track_cuts ) > 0:
                    cuts.append( track_cuts )

            log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : 'Raw cuts are: %s' % ( cuts ) } ) )

            # Sort all our tracks by the start time of the tracks.
            sorted_track_cuts = sorted( [ x for y in cuts for x in y ], key=lambda element: element[0] )
            
            log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : 'Sorted cuts are: %s' % ( sorted_track_cuts ) } ) )

            # And concatenate overlapping tracks.
            # 
            # NOTE: We allow here cuts longer than our maximum.
            final_cuts = [ [ -1, -1 ] ]
            for cut in sorted_track_cuts:
                if final_cuts[-1][0] <= cut[0] and final_cuts[-1][1] >= cut[0]:
                    final_cut = max( cut[1], final_cuts[-1][1] )
                    final_cuts[-1][1] = final_cut
                else:
                    final_cuts.append( cut )
            final_cuts = final_cuts[1:]

            log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : 'Final cuts are: %s' % ( final_cuts ) } ) )

            # Stop working on this input video if there were no cuts of interest.
            if len( final_cuts ) == 0:
                continue

            # Download the movie and get its aspect ratio.
            movie_key = '%s/%s_output.mp4' % ( media_uuid, media_uuid )
            movie_file = '%s/%s.mp4' % ( workdir, media_uuid )
            download_file( movie_file, config.bucket_name, movie_key )
            log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                    'message'   : 'Dowloaded input video to %s' % ( movie_file ) } ) )


            exif = get_exif( media_uuid, movie_file )
            input_x = int( exif['width'] )
            input_y = int( exif['height'] )
            input_ratio = float( input_x ) / input_y
            log.debug( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : 'Got exif for input video of dimension: %sx%s' % ( input_x, input_y ) } ) )

            # Calculate the aspect ratio for our output video.
            output_ratio = float( output_x ) / output_y

            # Generate our clips.
            for idx, track_cut in enumerate( final_cuts ):
                cut_video = "%s/%s_%s.mp4" % ( workdir, media_uuid, idx )

                if input_ratio < output_ratio:
                    ffmpeg_opts = ' -vf scale=-1:%s,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_y, output_x, output_y )
                else:
                    ffmpeg_opts = ' -vf scale=%s:-1,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_x, output_x, output_y )
                cmd = "ffmpeg -y -i %s -ss %s -t %s -r 24 %s %s" % ( movie_file, track_cut[0], track_cut[1]-track_cut[0], ffmpeg_opts, cut_video )

                log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                         'message'   : 'Generating clip with command: %s' % ( cmd ) } ) )
                ( status, output ) = commands.getstatusoutput( cmd )

                if status == 0:
                    # Store the fact that we made this cut for later concatenation.
                    cut_lines.append( "file %s\n" % ( cut_video ) )
                else:
                    log.error( json.dumps( { 'user_uuid' : user_uuid, 
                                             'message'   : 'Something went wrong generating clip, output was: %s' % ( output ) } ) )
                    output_secs -= track_cut[1] - track_cut[0]
            
        except Exception as e:
            log.error( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : 'Unexpected error processing file %s: %s' % ( media_uuid, e ) } ) )
            # Note - we just keep going if we hit an error and hope for the best.

    # Open the output file for storing concatenation data.
    cut_file_name = '%s/cuts.txt' % ( workdir )
    cut_file = open( cut_file_name, 'w' )

    random.shuffle( cut_lines )
    for line in cut_lines:
        cut_file.write( line )

    cut_file.close()

    if output_secs > min_output_secs:
        return True
    else:
        log.warning( json.dumps( { 'user_uuid' : user_uuid, 
                                   'message'   : 'Summary video length of %s was too short, returning False.' % ( output_secs ) } ) )
        return False
                
def produce_summary_video( user_uuid, workdir, viblio_added_content_id ):
    # Open the output file for storing concatenation data.
    cut_file_name = '%s/cuts.txt' % ( workdir )
    output_file = '%s/summary.mp4' % ( workdir )

    if not os.path.isfile( cut_file_name ):
        raise Exception( "Coudn't find expected cut file at: %s" % ( cut_file_name ) )

    cmd = "ffmpeg -y -f concat -i %s %s" % ( cut_file_name, output_file )
    log.info( json.dumps( { 'user_uuid' : user_uuid, 
                            'message'   : 'Generating summary with command: %s' % ( cmd ) } ) )

    ( status, output ) = commands.getstatusoutput( cmd )

    if status != 0:
        message = "Error generating summary video: %s" % ( output )
        log.error( json.dumps( { 'user_uuid' : user_uuid, 
                                     'message'   : message } ) )
        raise Exception( message )
    else:
        # Upload video to S3.
        summary_uuid = str( uuid.uuid4() )
        log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                'message'   : 'Uploading summary video from %s with uuid %s' % ( output_file, summary_uuid ) } ) )
        upload_file( output_file, config.bucket_name, "%s/%s" % ( summary_uuid, summary_uuid ) )

        # Write records to database
        orm = vib.db.orm.get_session()
        orm.commit()

        unique_hash = None
        f = open( output_file, 'rb' )
        md5 = hashlib.md5()
        while True:
            file_data = f.read( 1048576 )
            if not file_data:
                break
            md5.update( file_data )
        unique_hash = md5.hexdigest()
        f.close()

        log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                'message'   : 'Creating database records for user_uuid %s, media_uuid %s, and viblio_added_contet_id %s ' % ( user_uuid, summary_uuid, viblio_added_content_id ) } ) )

        user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()
        media = Media( uuid = summary_uuid,
                       media_type = 'original',
                       filename = 'Faces Summary',
                       title = 'A Gift from Viblio',
                       view_count = 0,
                       status = 'pending',
                       is_viblio_created = True,
                       unique_hash = unique_hash )
        user.media.append( media )

        original_uuid = str( uuid.uuid4() )

        video_asset = MediaAssets(
            uuid = original_uuid,
            asset_type = 'original',
            bytes = os.path.getsize( output_file ),
            uri = "%s/%s" % ( summary_uuid, summary_uuid ),
            location = 'us',
            view_count = 0 )
        media.assets.append( video_asset )

        vac = orm.query( ViblioAddedContent ).filter( ViblioAddedContent.id == viblio_added_content_id ).one()
        vac.status = 'prepared'
        media.viblio_added_content.append( vac )
        
        orm.commit()
        orm.close()

        # New pipeline callout
        log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                'message'   : 'Starting VWF execution.' } ) )
        execution = swf.WorkflowType( 
            name = 'VideoProcessing' + config.VPWSuffix, 
            domain = 'Viblio', version = '1.0.7' 
            ).start( 
            task_list = 'VPDecider' + config.VPWSuffix + config.UniqueTaskList, 
            input = json.dumps( { 
                        'viblio_added_content_type' : 'Smiling Faces',
                        'media_uuid' : summary_uuid, 
                        'user_uuid'  : user_uuid,
                        'original_uuid' : original_uuid,
                        'input_file' : {
                            's3_bucket'  : config.bucket_name,
                            's3_key' : "%s/%s" % ( summary_uuid, summary_uuid ),
                            },
                        'metadata_uri' : None,
                        'outputs' : [ { 
                                'output_file' : {
                                    's3_bucket' : config.bucket_name,
                                    's3_key' : "%s/%s_output.mp4" % ( summary_uuid, summary_uuid ),
                                    },
                                'format' : 'mp4',
                                'max_video_bitrate' : 1500,
                                'audio_bitrate' : 160,
                                'asset_type' : 'main',
                                'thumbnails' : [ {
                                        'times' : [ 0.5 ],
                                        'type'  : 'static',
                                        'size'  : "320x240",
                                        'label' : 'poster',
                                        'format' : 'png',
                                        'output_file' : {
                                            's3_bucket' : config.bucket_name,
                                            's3_key' : "%s/%s_poster.png" % ( summary_uuid, summary_uuid ),
                                            }
                                        }, 
                                                 {
                                        'times' : [ 0.5 ],
                                        'type'  : 'static',
                                        'original_size' : True,
                                        'label' : 'poster_original',
                                        'format' : 'png',
                                        'output_file' : {
                                            's3_bucket' : config.bucket_name,
                                            's3_key' : "%s/%s_poster_original.png" % ( summary_uuid, summary_uuid ),
                                            }
                                        }, 
                                                 {
                                        'times' : [ 0.5 ],
                                        'size': "128x128",
                                        'type'  : 'static',
                                        'label' : 'thumbnail',
                                        'format' : 'png',
                                        'output_file' : {
                                            's3_bucket' : config.bucket_name,
                                            's3_key' : "%s/%s_thumbnail.png" % ( summary_uuid, summary_uuid ),
                                            }
                                        },
                                                 {
                                        'times' : [ 0.5 ],
                                        'type'  : 'animated',
                                        'size'  : "320x240",
                                        'label' : 'poster_animated',
                                        'format' : 'gif',
                                        'output_file' : {
                                            's3_bucket' : config.bucket_name,
                                            's3_key' : "%s/%s_poster_animated.gif" % ( summary_uuid, summary_uuid ),
                                            }
                                        },
                                                 {
                                        'times' : [ 0.5 ],
                                        'size': "128x128",
                                        'type'  : 'animated',
                                        'label' : 'thumbnail_animated',
                                        'format' : 'gif',
                                        'output_file' : {
                                            's3_bucket' : config.bucket_name,
                                            's3_key' : "%s/%s_thumbnail_animated.gif" % ( summary_uuid, summary_uuid ),
                                            }
                                        } ]
                                }
                                      ]
                        } ),
            workflow_id=summary_uuid
            )

        # Clean up
        if workdir[:4] == '/mnt':
            log.info( json.dumps( { 'user_uuid' : user_uuid, 
                                    'message'   : 'Deleting temporary files at %s' % ( workdir ) } ) )
            shutil.rmtree( workdir )
        return
        
def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

def run():
    try:
        sqs = __get_sqs().get_queue( config.smile_creation_queue )

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
            log.debug( json.dumps( { 'message' : "Error converting options to string: %e" % e } ) )
        
        user_uuid           = options.get( 'user_uuid', None )
        viblio_added_content_id = options['viblio_added_content_id']
        min_clip_secs       = float( options.get( 'min_clip_secs', 2.5 ) )
        max_clip_secs       = float( options.get( 'max_clip_secs', 5 ) )
        max_input_videos    = int( options.get( 'max_input_videos', 120 ) )
        max_secs_per_input  = int( options.get( 'max_secs_per_input', 30 ) )
        max_clips_per_input = int( options.get( 'max_clips_per_input', 3 ) )
        min_output_secs     = int( options.get( 'min_output_secs', 6 ) )
        max_output_secs     = int( options.get( 'max_output_secs', 120 ) )
        output_x            = int( options.get( 'output_x', 640 ) )
        output_y            = int( options.get( 'output_y', 360 ) )

        if user_uuid != None:
            workdir = config.faces_dir + '/smiling_faces/' + user_uuid
            try:
                if not os.path.isdir( workdir ):
                    os.makedirs( workdir )
            except Exception as e:
                log.error( json.dumps( { 'message' : "Error creating workdir %s: %e" % ( workdir, e ) } ) )
                raise

            clips_ok = generate_clips( user_uuid, 
                                       workdir             = workdir,
                                       min_clip_secs       = min_clip_secs,
                                       max_clip_secs       = max_clip_secs,
                                       max_input_videos    = max_input_videos,
                                       max_secs_per_input  = max_secs_per_input,
                                       max_clips_per_input = max_clips_per_input,
                                       min_output_secs     = min_output_secs,
                                       max_output_secs     = max_output_secs,
                                       output_x            = output_x, 
                                       output_y            = output_y )
            if clips_ok:
                produce_summary_video( user_uuid, workdir, viblio_added_content_id )
                
            log.info( json.dumps( { 'message' : "Completed succesfully for user_uuid: %s" % ( user_uuid ) } ) )
            sqs.delete_message( message )
            return True
        else:
            # This message is not for us or is malformed, someone else
            # can deal with it.
            return True

        return True

    except Exception as e:
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise
    finally:
        if message != None and options != None:
            # Even if something went wrong, make sure we delete the
            # message so we don't end up stuck in an infinite loop
            # trying to process this message.
            sqs.delete_message( message )    
