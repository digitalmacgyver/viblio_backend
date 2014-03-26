#!/usr/bin/env python

'''

recognition_input = media_uuid + '/' + media_uuid + '_recognition_input.json'

General approach:

Options:

2) This is kicked off by a selector script.

We get in a user_uuid.

1) Parametrzie everything:

* user_uuid
* min_clip_secs
* max_clip_secs
* max_input_videos
* max_length_per_input_video
* max_clips_per_input_video
* min_output_length
* max_output_length

2) Clean up code / segment it.

3) Design DB schema elements.

First decide on the logic writ large: when do we try to send this ( 3 days, after 10 videos, what? )

* Which videos are user videos and which are promotional
* Which users have we attempted this for (even if they have deleted the summary)

4) Write data into the users account.

4) Design email.

5) Communicate with Andy on how to do the email.

First try this manually for an account like Mona's 418:
'''


import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
import commands
import datetime
import json
import logging
from logging import handlers
import math
import os
from sqlalchemy import and_
import time
import uuid

import vib.db.orm
from vib.db.models import *
from vib.utils.s3 import download_string, download_file
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
                    workdir             = workdir,
                    min_clip_secs       = min_clip_secs,
                    max_clip_secs       = max_clip_secs,
                    max_input_videos    = max_input_videos,
                    max_secs_per_input  = max_secs_per_input,
                    max_clips_per_input = max_clips_per_input,
                    min_output_secs     = min_output_secs,
                    max_output_secs     = max_output_secs ):
    '''Takes the input parameters:
    user_uuid, 
    workdir             = Temporary directory to store videos and clips
    min_clip_secs       = Default 1. No clips shorter than this will be included.
    max_clip_secs       = Default 3. No clips longer than this will be included.
    max_input_videos    = Default 120. At most this many videos with faces will be considered.
    max_secs_per_input  = Default 9. Once this threshold is reached, no
                          more clips will be added from this input.
    max_clips_per_input = Default 3. At most this many clips will be included per input.
    min_output_secs     = If this threshold is not reached, return false.
    max_output_secs     = Default 120.  One this threshold is reached, no more clips will 
                          be added.

    NOTE: If max_clip_secs*max_clips_per_input != max_secs_per_input
    then the lesser of the two will determine when we stop including
    clips from a video.
    '''

    # Get the list of movies for the current user.
    orm = vib.db.orm.get_session()
    orm.commit()

    user = orm.query( Users ).filter( User.uuid = user_uuid ).one()
    
    media_files = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.status == 'complete' ) ).order_by( Media.recording_date )[:]

    # Open the output file for storing concatenation data.
    cut_file_name = '%/cuts.txt' % workdir
    cut_file = open( cut_file_name, 'w' )

    output_secs = 0
    output_clips = 0

    for media in media_files:
        if running_total >= max_output_secs:
            continue
        
        if output_clips >= max_input_videos:
            continue

        media_uuid = media.uuid

        try:
            # Where various things are located.
            visibility_key = '%s/%s_recognition_input.json' % ( media_uuid, media_uuid )
            movie_key = '%s/%s_output.mp4' % ( media_uuid, media_uuid )
            movie_file = '%s/%s.mp4' % ( workdir, media_uuid )

            # If there is a valid data structure for us to see faces in this video.
            #
            # NOTE: Many videos will not have this data strucure, that
            # is fine, just skip those.
            tracks = json.loads( download_string( config.bucket_name, visibility_key ) )['tracks']
            g = open( "%s/%s_tracks.json" % ( workdir, media_uuid ), 'w' )
            json.dump( tracks, g )
            g.close()

            input_secs = 0
            input_clips = 0
            cuts = [ ]
            for track in tracks:
                # Stop working on this input if we've got all we need from it.
                if input_secs >= max_secs_per_input:
                    continue
                if input_clips >= max_clips_per_input:
                    continue

                # Skip tracks where the person isn't happy.
                if not track['faces'][0]['isHappy']:
                    continue

                track_cuts = [ [ -1, -1 ] ]
                for vi in track['visiblity_info']:
                #print "Raw start/end is: %s/%s" % ( vi['start_frame'], vi['end_frame'] )
                start = float( vi['start_frame'] )/1000
                end = math.ceil( float( vi['end_frame'] )/1000 )
                if end - start < 1:
                    print "Skipping short cut less than 1 second."
                    continue
                elif end - start > 3:
                    print "Trimming segment down to 3 seconds"
                    end = start + 3
                #print "Computed start/end is: %s/%s" % ( start, end )
                running_total += end - start
                video_total += end - start
                if track_cuts[-1][1] >= start:
                    new_start = track_cuts[-1][0]
                    new_end = max( end, track_cuts[-1][1] )
                    #print "Adjusted start/end is: %s/%s" % ( new_start, new_end )
                    track_cuts[-1] = [ new_start, new_end ]
                else:
                    track_cuts.append( [ start, end ] )
            if len( track_cuts ) > 1:
                cuts.append( track_cuts[1:] )
        print cuts
        sorted_track_cuts = sorted( [ x for y in cuts for x in y ], key=lambda element: element[0] )
        final_cuts = [ [ -1, -1 ] ]
        for cut in sorted_track_cuts:
            if final_cuts[-1][0] < cut[0] and final_cuts[-1][1] > cut[0]:
                final_cut = max( cut[1], final_cuts[-1][1] )
                final_cuts[-1][1] = final_cut
            else:
                final_cuts.append( cut )
        final_cuts = final_cuts[1:]
        if len( final_cuts ) == 0:
            continue
        print final_cuts
        download_file( movie_file, config.bucket_name, movie_key )
        #cmd = "ffmpeg -i %s " % ( movie_file )
        exif = get_exif( media_uuid, movie_file )
        input_x = int( exif['width'] )
        input_y = int( exif['height'] )
        input_ratio = float( input_x ) / input_y
        output_x = 640
        output_y = 360
        output_ratio = float( output_x ) / output_y
        for idx, track_cut in enumerate( final_cuts ):
            cut_video = "/tmp/%s_%s.mp4" % ( media_uuid, idx )
            if input_ratio < output_ratio:
                ffmpeg_opts = ' -vf scale=-1:%s,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_y, output_x, output_y )
            else:
                ffmpeg_opts = ' -vf scale=%s:-1,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_x, output_x, output_y )
            cmd = "ffmpeg -i %s -ss %s -t %s -r 24 %s %s" % ( movie_file, track_cut[0], track_cut[1]-track_cut[0], ffmpeg_opts, cut_video )
            cut_file.write( "file %s\n" % ( cut_video ) )
            #print "Runnning:", cmd
            ( status, output ) = commands.getstatusoutput( cmd )
            #print "Output was:", output
    except Exception as e:
        print "ERROR WAS %s" % ( e ) 

cut_file.close()

cmd = "ffmpeg -y -f concat -i %s %s" % ( cut_file, output_file )
( status, output ) = commands.getstatusoutput( cmd )





def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

sqs = __get_sqs().get_queue( config.new_account_creation_queue )
sqs.set_message_class( RawMessage )

def run():
    try:
        message = None
        message = sqs.read( wait_time_seconds = 20 )

        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()

        try:
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body was %s: " % body } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % e } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % options } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %e" % e } ) )
        
        user_uuid = options.get( 'user_uuid', None )
        min_clip_secs = float( options.get( 'min_clip_secs', 1 ) )
        max_clip_secs = float( options.get( 'max_clip_secs', 3 ) )
        max_input_videos = int( options.get( 'max_input_videos', 120 ) )
        max_secs_per_input = int( options.get( 'max_secs_per_input', 30 ) )
        max_clips_per_input = int( options.get( 'max_clips_per_input', 3 ) )
        min_output_secs = int( options.get( 'min_output_secs', 6 ) )
        max_output_secs = int( options.get( 'max_output_secs', 120 ) )

        if user_uuid != None:
            workdir = config.faces_dir + '/smiling_faces/' + user_uuid,
            clips_ok = generate_clips( user_uuid, 
                                       workdir             = workdir,
                                       min_clip_secs       = min_clip_secs,
                                       max_clip_secs       = max_clip_secs,
                                       max_input_videos    = max_input_videos,
                                       max_secs_per_input  = max_secs_per_input,
                                       max_clips_per_input = max_clips_per_input,
                                       min_output_secs     = min_output_secs,
                                       max_output_secs     = max_output_secs )
            if clips_ok:
                produce_summary_video( user_uuid, workdir )
                
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
