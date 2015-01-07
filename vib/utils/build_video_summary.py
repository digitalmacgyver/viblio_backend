#!/usr/bin/env python

'''
Takes in requests from the UI, and builds video summaries around a set
of selected images or contacts.

The caller is responsible for enforcing access controls.

{
    'user_uuid' : uuid of the user to generate the summary for.
    'images[]' : [ # Array of images to be used in the summary
        image1_uuid,
        image2_uuid,
        ... ],
    'summary_type' : 'moments', # One of a predefined list of summary
				# types, e.g. moments, people, etc.
    'audio_track' : media_uuid # The UUID of the audio selected for
			       # this track.

    'contacts[]' : [ # Who the summary should include, required if
		   # summary_type is 'people', optional otherwise.
		   # NOTE: Initially we will only support the
		   # 'moments' type summary that won't use this most
		   # likely.
        contact1_uuid,
        ... ],
    'videos[]' : [ video1_uuid, ... ] # An array of videos to
				      # summarize for the 'people'
				      # type of summary.

# Optional parameters:

    'output_x' : 640, # Output summary dimensions in pixels.
    'output_y' : 360,

# Summary controls:
    'summary_style' : 'classic' # One of a predefined list of summary
				# types, e.g. classic, cascade, etc.
    'order' : 'random' # One of a predefined list of how we order
		       # clips, e.g. 'random', 'oldest', 'newest',
		       # etc.. Defaults to random.
    'effects[]' : [ 'vintage', 'music video', ... ] # List of preset
						  # video filters the
						  # user wants us to
						  # provide. NOTE:
						  # Initially this may
						  # not do anything.
    'moment_offsets[]' : [-2.5, 2.5] # How much before the image to
				   # start the summary clip, and how
				   # much after the moment to end the
				   # summary clip, defaults to [-2.5,
				   # 2.5]
    'target_duration' : 99 #The desired number of seconds the summary
			   #will run. Defaults to something sane given
			   #the clips selected and audio selected.
    'summary_options' : { } # Defaults to {} Generic JSON to be passed
			    # to the summary API for future expansions
			    # (e.g. parameters that control blur, slow
			    # motion, ??? ).

# Where to put the summary:
    'album_uuid' : album_uuid # An album to place the resulting
			      # summary into.

# Summary metadata:
    'title' : 'Fun Times!', # OPTIONAL: A title for the video -
			    # defaults "Summary - YYYY-MM-DD" - I
			    # suggest the UI overwrite this with
			    # "FilterName Summary"
    'description' : "Vacation", # OPTIONAL: A description for the
				# video - defaults to nothing.
    'lat' : X, 'lng' : Y, 'geo_city' : Z, # Defaults to nothing
    'tags[]' : [ tag1, tag2, ... ], # Defaults to nothing.
    'recording_date' : 'when' # Defaults to now.
}

'''


import boto.swf.layer2 as swf
import boto.sqs
import boto.sqs.connection
from boto.sqs.message import RawMessage
import commands
import datetime
import glob
import hashlib
import json
import logging
from logging import handlers
import math
import os
import random
import re
import shutil
from sqlalchemy import and_
import time
import uuid

import vib.db.orm
from vib.db.models import *
from vib.utils.s3 import download_string, download_file, upload_file
import vib.utils.vsum as vsum

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'build_video_summary: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def download_movie( media_uuid, workdir ):
    movie_key = '%s/%s_output.mp4' % ( media_uuid, media_uuid )
    movie_file = '%s/%s.mp4' % ( workdir, media_uuid )
    download_file( movie_file, config.bucket_name, movie_key )
    log.info( json.dumps( { 'media_uuid' : media_uuid, 
                            'message'   : 'Downloaded input video to %s' % ( movie_file ) } ) )
    return movie_file


def get_moments( media_uuid, images, order, workdir, moment_offsets, random_duration=False, min_duration=None ):
    '''Returns a data structure:
    { summary_duration : 99
      videos : { 
        video1_uuid : {
          filename : /tmp/video.mp4,
          cuts : [ ( 0, 3 ), ( 2, 5 ), ... ]
        }, 
        ...
      }
    }
    '''
    # Get the list of movies for the input images.
    orm = vib.db.orm.get_session()
    orm.commit()

    # Fields here are x.Media.whatever, and x.MediaAssets.uuid.
    videos = orm.query( Media, MediaAssets ).filter( 
        Media.id == MediaAssets.media_id,
        Media.is_album == 0,
        MediaAssets.uuid.in_( images ) ).order_by( Media.recording_date.desc(), Media.created_date.desc(), MediaAssets.timecode )[:]

    if order == 'oldest':
        # Sort from oldest to newest, but still show clips from within
        # a given video in order.
        videos.sort( key=lambda x: ( x.Media.recording_date, x.Media.created_date, x.MediaAssets.timecode ) )

    #import pdb
    #pdb.set_trace()

    if order == 'random':
        random.shuffle( videos )

    result = { 'summary_duration' : None,
               'videos' : {} }
    summary_duration = 0
    prior_video_uuid = None
    for video_index, video in enumerate( videos ):

        timecode = float( video.MediaAssets.timecode )

	start_offset = moment_offsets[0]
	end_offset = moment_offsets[1]
	if random_duration:
	    start_offset *= random.uniform( 1, 2 )
	    end_offset *= random.uniform( 1, 2 )

        if video.Media.uuid not in result['videos']:
            movie_file = download_movie( video.Media.uuid, workdir )

	    result['videos'][video.Media.uuid] = { 'filename' : movie_file, 
						   'video_index' : video_index }
            
            ( status, output ) = commands.getstatusoutput( 'ffprobe -v quiet -print_format json -show_format -show_streams %s ' % ( movie_file ) )
            info = json.loads( output )
            video_duration = float( info['format']['duration'] )
	    result['videos'][video.Media.uuid]['duration'] = video_duration

            start = max( 0,              timecode + start_offset )
            end   = min( video_duration, timecode + end_offset )
	    
	    if min_duration is None or end - start >= min_duration:
		result['videos'][video.Media.uuid]['cuts'] = [ [ start, end ] ]
		summary_duration += end - start
	    else:
		result['videos'][video.Media.uuid]['cuts'] = [ ]

        else:
            video_duration = result['videos'][video.Media.uuid]['duration']

            start = max( 0,              timecode + start_offset )
            end   = min( video_duration, timecode + end_offset )
            
            if order in [ 'oldest', 'newest' ]:
                if prior_video_uuid == video.Media.uuid:
                    # If we're working on sequential cuts from the
                    # same video, don't let them overlap.
		    if len( result['videos'][video.Media.uuid]['cuts'] ):
			start = max( start, result['videos'][video.Media.uuid]['cuts'][-1][1] )

                    if start >= end:
                        continue

	    if min_duration is None or end - start >= min_duration:
		result['videos'][video.Media.uuid]['cuts'].append( [ start, end ] )
		summary_duration += end - start

        prior_video_uuid = video.Media.uuid
            
    result['summary_duration'] = summary_duration

    return result


def pad_clips( w1, w1_clips, w2_clips, bgcolor='White', summary_options={} ):
    '''Takes in two arrays of clips, and if the duration of clips in
    w2_clips exceeds those in w1_clips, adds some blank screens of bgcolor
    to w1_clips so they have the same duration.  Returns the augmented set
    of w1_clips.'''

    width = w1.width
    height = w1.height

    w1_duration = 0
    for clip in w1_clips:
        w1_duration += clip.get_duration()

    w2_duration = 0
    for clip in w2_clips:
        w2_duration += clip.get_duration()

    if w2_duration > ( w1_duration + 0.01 ):
        total_pad = w2_duration - w1_duration
        
        intersperse = False

        # This technique intersperses the pads.
        if intersperse:
            num_pads = max( 1, len( w1_clips ) - 1 )
            pads = []
            for i in range( num_pads ):

                bgimage_file = None
                if summary_options.get( 'holiday_card', False ):
                    if width == 368:
                        bgimage_file = "%s/media/w1-underlay.png" % ( os.path.dirname( __file__ ) )
                    elif width == 656:
                        bgimage_file = "%s/media/w2-underlay.png" % ( os.path.dirname( __file__ ) )

                pads.append( vsum.Clip( vsum.Video( vsum.get_solid_clip( float( total_pad ) / num_pads, width, height, bgcolor, bgimage_file ) ) ) )
            
            result = []

            for i in range( max( len( pads ), len( w1_clips ) ) ):
                if i < len( w1_clips ):
                    result.append( w1_clips[i] )
                if i < len( pads ):
                    result.append( pads[i] )

            return result
        else:
            # This technique puts the pads at the beginning and end.
            bgimage_file = None
            if summary_options.get( 'holiday_card', False ):
                if width == 368:
                    bgimage_file = "%s/media/w1-underlay.png" % ( os.path.dirname( __file__ ) )
                elif width == 656:
                    bgimage_file = "%s/media/w2-underlay.png" % ( os.path.dirname( __file__ ) )
            pad = vsum.Clip( vsum.Video( vsum.get_solid_clip( float( total_pad ) / 2, width, height, bgcolor, bgimage_file ) ) )
            return [ pad ] + w1_clips + [ pad ]

    # Nothing to do.
    return w1_clips


def generate_summary( summary_type,
                      summary_uuid,
                      user_uuid,
                      images,
                      workdir,
                      audio_track,
                      contacts        = [],
                      videos          = [],
                      album_uuid      = None,
                      summary_style   = 'classic',
                      order           = 'random',
                      effects         = [],
                      moment_offsets  = ( -2.5, 2.5 ),
                      target_duration = None,
                      summary_options = {},
                      title           = '',
                      description     = '',
                      lat             = None,
                      lng             = None,
                      tags            = [],
                      recording_date  = None,
                      output_x        = 1280,
                      output_y        = 720 ):

    vsum.Window.set_tmpdir( "%s/../vsum_tmp" % workdir )

    output_file = "%s/%s.mp4" % ( workdir, summary_uuid )

    orm = vib.db.orm.get_session()
    audio_track = orm.query( Media, MediaAssets ).filter( Media.id == MediaAssets.media_id,
                                                          Media.uuid == audio_track,
                                                          MediaAssets.asset_type == 'original' ).one()

    audio_filename = "%s/%s_audio" % ( workdir, summary_uuid )
    audio_desc = audio_track.Media.description
    if audio_desc is None:
        audio_desc = ''
    download_file( audio_filename, config.bucket_name, audio_track.MediaAssets.uri )

    # While get_moments will return things with the approrpriate
    # order, we can tell vsum.distribute_clips to randomize clips, if
    # we do then when it loops clips to make a min_duration they will
    # not keep appearing in the same order with each loop.
    randomize_clips = False
    if order == 'random':
        randomize_clips = True

    if summary_type == 'moments':
	if summary_style != 'cascade':
	    video_cuts = get_moments( summary_uuid, images, order, workdir, moment_offsets )
	else:
	    video_cuts = get_moments( summary_uuid, images, order, workdir, moment_offsets, random_duration=True, min_duration = float( moment_offsets[1]-moment_offsets[0] )/2 )

        summary_clips = []
        for video_uuid, video in sorted( video_cuts['videos'].items(), key=lambda x: x[1]['video_index'] ):
            filename = video['filename']
            cuts = video['cuts']
            
            for cut in cuts:
                summary_clips.append( vsum.Clip( video = vsum.Video( filename=filename ),
                                                 start = cut[0],
                                                 end   = cut[1] ) )

        bgimage = None
        if summary_options.get( 'holiday_card', False ):
            bgimage = "%s/media/stock-background-1280-720.png" % ( os.path.dirname( __file__ ) )

        w = vsum.Window( width       = output_x, 
                         height      = output_y, 
                         output_file = output_file, 
                         duration    = target_duration,
                         bgcolor     = "White",
                         audio_filename  = audio_filename,
                         audio_desc  = audio_desc,
                         bgimage_file = bgimage )
        w.display.pad_bgcolor = 'White'

        small_logo_color = 'white'
        large_logo_color = 'white'
		
	if summary_style == 'classic':
	    w.display.display_style = vsum.PAD
	    vsum.distribute_clips( summary_clips, [ w ], min_duration=target_duration, randomize_clips=randomize_clips )
            
        elif summary_style == 'cascade':
            small_logo_color = 'gray'
            large_logo_color = 'gray'
            w.display.display_style = vsum.OVERLAY
	    w.bgcolor = 'LightGrey'
	    w.bgimage_file = "%s/media/logo-white-1280x720.png" % ( os.path.dirname( __file__ ) )
            vsum.distribute_clips( summary_clips, [ w ], min_duration=target_duration, randomize_clips=randomize_clips )
        elif summary_style == 'template-1':
            large_logo_color = 'gray'
            w1 = vsum.Window( width=512, height=312, x=32, y=32, display=vsum.Display( display_style=vsum.CROP ) )
            w2 = vsum.Window( width=512, height=312, x=576, y=32, display=vsum.Display( display_style=vsum.PAD, pad_bgcolor="Blue" ) )
            w3 = vsum.Window( width=512, height=312, x=32, y=376, display=vsum.Display( display_style=vsum.PAN ) )
            w4 = vsum.Window( width=512, height=312, x=576, y=376, display=vsum.Display( display_style=vsum.OVERLAY ), bgcolor="Red" )
            w.windows = [ w1, w2, w3, w4 ]
            vsum.distribute_clips( summary_clips, [ w1, w2, w3, w4 ], min_duration=target_duration, randomize_clips=randomize_clips )
        elif summary_style == 'template-2':
            small_logo_color = 'gray'
            large_logo_color = 'white'
            w1 = vsum.Window( width=368, height=656, x=824, y=32, display=vsum.Display( display_style=vsum.CROP ) )
            w2 = vsum.Window( width=656, height=656, x=84, y=32, display=vsum.Display( display_style=vsum.PAN ) )
            w.windows = [ w1, w2 ]

            if summary_options.get( 'holiday_card', False ):
                w1.bgimage_file = "%s/media/w1-underlay.png" % ( os.path.dirname( __file__ ) )
                w2.bgimage_file = "%s/media/w2-underlay.png" % ( os.path.dirname( __file__ ) )

            if summary_options.get( 'distribute_clips', '' ) == 'side_by_side':
                # In this case we put clips side by side from the same
                # video, and add some padding of white only screens to
                # keep the durations the same.
                
                current_movie = summary_clips[0].video.filename
                w1_clips = []
                w2_clips = []

                for clip in summary_clips:
                    if clip.video.filename != current_movie:
                        w1.clips += pad_clips( w1, w1_clips, w2_clips, summary_options=summary_options )
                        w2.clips += pad_clips( w2, w2_clips, w1_clips, summary_options=summary_options )

                        # Reset the state for the next clip.
                        current_movie = clip.video.filename
                        w1_clips = []
                        w2_clips = []
                        if random.randint( 0, 1 ):
                            w1_clips.append( clip )
                        else:
                            w2_clips.append( clip )
                    else:
                        w1_duration = 0
                        for w1_clip in w1_clips:
                            w1_duration += w1_clip.get_duration()

                        w2_duration = 0
                        for w2_clip in w2_clips:
                            w2_duration += w2_clip.get_duration()

                        if w1_duration > w2_duration:
                            w2_clips.append( clip )
                        elif w2_duration > w1_duration:
                            w1_clips.append( clip )
                        else:
                            # If both screens have the same duration
                            # randomly pick one for the next clip to
                            # go in.
                            if random.randint( 0, 1 ):
                                w1_clips.append( clip )
                            else:
                                w2_clips.append( clip )
                
                w1.clips += pad_clips( w1, w1_clips, w2_clips, summary_options=summary_options )
                w2.clips += pad_clips( w2, w2_clips, w1_clips, summary_options=summary_options )

            else:
                vsum.distribute_clips( summary_clips, [ w1, w2 ], min_duration=target_duration, randomize_clips=randomize_clips )

        else:
            raise Exception( "Unexpected summary style: %s" % ( summary_style ) )

        m1 = vsum.Watermark( "%s/media/logo-%s-128.png" % ( os.path.dirname( __file__ ), small_logo_color ),
                             x = "main_w-overlay_w-10",
                             y = "main_h-overlay_h-10",
                             fade_out_start = 3,
                             fade_out_duration = 1 )
        m2 = vsum.Watermark( "%s/media/logo-%s-256.png" % ( os.path.dirname( __file__ ), large_logo_color ),
                        x = "trunc((main_w-overlay_w)/2)",
                             y = "trunc((main_h-overlay_h)/2)",
                             fade_in_start = -2,
                             fade_in_duration = 1 )
        w.watermarks = [ m1, m2 ]

        # DEBUG - try to make overall window the length of the longest
        # subwindow if nothing else is specified.
        if target_duration is None:
            window_duration = 0
            if w.windows is not None and len( w.windows ):
                window_duration = min( [ x.compute_duration( x.clips ) for x in w.windows ] )
            else:
                window_duration = w.compute_duration( w.clips )
            
            if summary_options.get( 'duration_method', '' ) == 'shortest':
                if w.duration is None or window_duration < w.duration:
                    w.duration = window_duration

        w.render()

    else:
        # DEBUG - implement other summary types.
        pass

    # Upload video to S3.
    log.info( json.dumps( { 'media_uuid' : summary_uuid, 
                            'message'    : 'Uploading summary video from %s with uuid %s' % ( output_file, summary_uuid ) } ) )
    upload_file( output_file, config.bucket_name, "%s/%s" % ( summary_uuid, summary_uuid ) )
    
    # Write records to database
    orm = vib.db.orm.get_session()
    orm.commit()

    album = None
    if album_uuid is not None:
        album = orm.query( Media ).filter( Media.uuid == album_uuid ).one()

    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

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

    log.info( json.dumps( { 'media_uuid' : summary_uuid, 
                            'message'    : 'Creating database records for album_uuid %s, media_uuid %s' % ( album_uuid, summary_uuid ) } ) )

    media = orm.query( Media ).filter( Media.uuid == summary_uuid ).one()
    media.unique_hash = unique_hash

    #media = Media( uuid = summary_uuid,
    #               media_type = 'original',
    #               filename = filename,
    #               title = title,
    #               description = description,
    #               view_count = 0,
    #               status = 'pending',
    #               recording_date = recording_date,
    #               lat = lat,
    #               lng = lng,
    #               unique_hash = unique_hash,
    #               is_viblio_created = True )
    #user.media.append( media )
    orm.commit()

    if album is not None:
        media_album = MediaAlbums( album_id = album.id,
                                   media_id = media.id )
        orm.add( media_album )

    original_uuid = str( uuid.uuid4() )

    video_asset = MediaAssets(
        uuid = original_uuid,
        asset_type = 'original',
        bytes = os.path.getsize( output_file ),
        uri = "%s/%s" % ( summary_uuid, summary_uuid ),
        location = 'us',
        view_count = 0 )
    media.assets.append( video_asset )

    for tag in tags:
        feature = MediaAssetFeatures(
            feature_type = 'activity',
            coordinates = tag
            )
        video_asset.media_asset_features.append( feature )

    orm.commit()

    # New pipeline callout
    log.info( json.dumps( { 'media_uuid' : summary_uuid, 
                            'message'    : 'Starting VWF execution.' } ) )
    execution = swf.WorkflowType( 
	    name = 'VideoProcessing' + config.VPWSuffix, 
	    domain = 'Viblio', version = '1.0.7' 
	    ).start( 
	    task_list = 'VPDecider' + config.VPWSuffix + config.UniqueTaskList, 
	    input = json.dumps( { 
				    'media_uuid' : summary_uuid, 
				    'user_uuid'  : user.uuid,
				    'original_uuid' : original_uuid,
                                    'viblio_added_content_type' : config.viblio_summary_video_type,
                                    'target_album_name' : config.viblio_summary_album_name,
                'template' : summary_options.get( 'template', None ),
                'subject' : summary_options.get( 'subject', None ),
                'year_desc' : summary_options.get( 'year_desc', None ),
                'album_name' : summary_options.get( 'album_name', None ),
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
								    'times' : [ 3.0 ],
								    'type'  : 'static',
								    'size'  : "288x216",
								    'label' : 'poster',
								    'format' : 'png',
								    'output_file' : {
									    's3_bucket' : config.bucket_name,
									    's3_key' : "%s/%s_poster.png" % ( summary_uuid, summary_uuid ),
									    }
								    }, 
								     {
								    'times' : [ 3.0 ],
								    'type'  : 'animated',
								    'size'  : "288x216",
								    'label' : 'poster_animated',
								    'format' : 'gif',
								    'output_file' : {
									    's3_bucket' : config.bucket_name,
									    's3_key' : "%s/%s_poster_animated.gif" % ( summary_uuid, summary_uuid ),
									    }
								    },
								     ]
						    }
						  ]
				    } ),
	    workflow_id=summary_uuid
	    )
	    
    # Clean up
    orm.close()
    if workdir[:4] == '/mnt':
        log.info( json.dumps( { 'media_uuid' : summary_uuid, 
				'message'    : 'Deleting temporary files at %s' % ( workdir ) } ) )
        shutil.rmtree( workdir )
    return

'''
# DEBUG - This code can be salvaged when we build people summaries.
    album = orm.query( Media ).filter( Media.uuid == album_uuid ).one()
    user = orm.query( Users ).filter( Users.id == album.user_id ).one()

    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                            'message'   : 'Getting media_files for user_id %s, album_id %s' % ( user.id, album.id ) } ) )

    if contact_id is not None:
        media_files = orm.query( Media.uuid, MediaAssetFeatures.track_id ).filter( 
            and_( 
                MediaAlbums.album_id == album.id,
                MediaAlbums.media_id == Media.id,
                Media.is_album == False,
                Media.status == 'complete', 
                Media.is_viblio_created == False,
                Media.id == MediaAssetFeatures.media_id,
                MediaAssetFeatures.contact_id == contact_id )
            ).order_by( Media.recording_date )[:]
    else:
        media_files = orm.query( Media.uuid, MediaAssetFeatures.track_id ).filter( 
            and_( 
                MediaAlbums.album_id == album.id,
                MediaAlbums.media_id == Media.id,
                Media.is_album == False,
                Media.status == 'complete', 
                Media.is_viblio_created == False,
                Media.id == MediaAssetFeatures.media_id )
            ).order_by( Media.recording_date )[:]
        
    orm.close()

    cut_lines = []

    output_secs = 0
    output_clips = 0

    media_tracks = {}
    for media in media_files:
        if media.uuid in media_tracks:
            media_tracks[media.uuid][media.track_id] = True
        else:
            media_tracks[media.uuid] = { media.track_id : True, "media" : media }

    for media_uuid in media_tracks.keys():
        media = media_tracks[media_uuid]["media"]
        media_uuid = media.uuid

        if output_secs >= max_output_secs:
            log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                    'message'   : 'max_output_secs limit reached, skipping analysis of media_uuid: %s' % ( media_uuid ) } ) )
            break
        
        if output_clips >= max_input_videos:
            log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                    'message'   : 'max_input_videos limit reached, skipping analysis of media_uuid: %s' % ( media_uuid ) } ) )
            break

        try:
            # Where various things are located.
            visibility_key = '%s/%s_recognition_input.json' % ( media_uuid, media_uuid )

            # If there is a valid data structure for us to see faces in this video.
            #
            # NOTE: Many videos will not have this data structure, that
            # is fine, just skip those.
            try: 
                tracks = json.loads( download_string( config.bucket_name, visibility_key ) )['tracks']
                g = open( "%s/%s_tracks.json" % ( workdir, media_uuid ), 'w' )
                json.dump( tracks, g )
                g.close()
                log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                        'message'   : 'Downloaded tracks for media_uuid: %s' % ( media_uuid ) } ) )
            except Exception as e:
                log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                        'message'   : "Couldn't download tracks for media_uuid: %s, skipping." % ( media_uuid ) } ) )
                continue

            input_secs = 0
            input_clips = 0
            cuts = [ ]

            for track in tracks:
                if track["track_id"] not in media_tracks[media_uuid]:
                    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                            'message'   : "Skipping track %s which does not have contact %s in it." % ( track["track_id"], contact_id ) } ) ) 
                    continue

                # Stop working on this input if we've got all we need from it.
                if input_secs >= max_secs_per_input:
                    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                            'message'   : 'max_secs_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                    break
                if input_clips >= max_clips_per_input:
                    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                            'message'   : 'max_clips_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                    break

                # Skip tracks where the person isn't happy.
                if 'isHappy' in track['faces'][0] and not track['faces'][0]['isHappy']:
                    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                            'message'   : 'Skipping track where person is not happy for media_uuid: %s' % ( media_uuid ) } ) )
                    continue

                track_cuts = [ ]

                for vi in track['visiblity_info']:
                    # Stop working on this input if we've got all we need from it.
                    if input_secs >= max_secs_per_input:
                        log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                                'message'   : 'max_secs_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                        break
                    if input_clips >= max_clips_per_input:
                        log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                                'message'   : 'max_clips_per_input limit reached, skipping additional tracks for media_uuid: %s' % ( media_uuid ) } ) )
                        break


                    start = float( vi['start_frame'] )/1000
                    end = float( vi['end_frame'] )/1000

                    # Skip clips that are too short.

                    # DEBUG - just extend clips to be 5 seconds if we can.
                    if end - start < 5:
                        current = end - start
                        start = max( 0, start - ( 5.0 - current ) / 2.0 )
                        end += ( 5.0 - current ) / 2.0

                    if end - start < min_clip_secs:
                        log.debug( json.dumps( { 'album_uuid' : album_uuid, 
                                                 'message'   : 'Skipping cut %s-%s because it is shorter than min_clip_secs' % ( start, end ) } ) )
                        continue

                    # Trim clips that are too long.
                    if end - start > max_clip_secs:
                        log.debug( json.dumps( { 'album_uuid' : album_uuid, 
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

            log.debug( json.dumps( { 'album_uuid' : album_uuid, 
                                     'message'   : 'Raw cuts are: %s' % ( cuts ) } ) )

            # Sort all our tracks by the start time of the tracks.
            sorted_track_cuts = sorted( [ x for y in cuts for x in y ], key=lambda element: element[0] )
            
            log.debug( json.dumps( { 'album_uuid' : album_uuid, 
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

            log.debug( json.dumps( { 'album_uuid' : album_uuid, 
                                     'message'   : 'Final cuts are: %s' % ( final_cuts ) } ) )

            # Stop working on this input video if there were no cuts of interest.
            if len( final_cuts ) == 0:
                continue

            # Download the movie and get its aspect ratio.
            movie_key = '%s/%s_output.mp4' % ( media_uuid, media_uuid )
            movie_file = '%s/%s.mp4' % ( workdir, media_uuid )
            download_file( movie_file, config.bucket_name, movie_key )
            log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                    'message'   : 'Downloaded input video to %s' % ( movie_file ) } ) )


            exif = get_exif( media_uuid, movie_file )
            input_x = int( exif['width'] )
            input_y = int( exif['height'] )
            input_ratio = float( input_x ) / input_y
            log.debug( json.dumps( { 'album_uuid' : album_uuid, 
                                     'message'   : 'Got exif for input video of dimension: %sx%s' % ( input_x, input_y ) } ) )

            # Calculate the aspect ratio for our output video.
            output_ratio = float( output_x ) / output_y

            # Generate our clips.
            for idx, track_cut in enumerate( final_cuts ):
                cut_video = "%s/%s_%s.mp4" % ( workdir, media_uuid, idx )

                # DEBUG - all we care about for now are that the
                # videos less than 640 wide and 360 high.
                if input_ratio < output_ratio:
                    ffmpeg_opts = ' -vf scale=-1:%s ' % ( output_y )
                else:
                    ffmpeg_opts = ' -vf scale=%s:-1 ' % ( output_x )

                #if input_ratio < output_ratio:
                #    ffmpeg_opts = ' -vf scale=-1:%s,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_y, output_x, output_y )
                #else:
                #    ffmpeg_opts = ' -vf scale=%s:-1,pad="%s:%s:(ow-iw)/2:(oh-ih)/2" ' % ( output_x, output_x, output_y )

                cmd = "ffmpeg -y -i %s -ss %s -t %s -r 30000/1001 -an %s %s" % ( movie_file, track_cut[0], track_cut[1]-track_cut[0], ffmpeg_opts, cut_video )

                log.info( json.dumps( { 'album_uuid' : album_uuid, 
                                         'message'   : 'Generating clip with command: %s' % ( cmd ) } ) )
                ( status, output ) = commands.getstatusoutput( cmd )

                if status == 0:
                    # Store the fact that we made this cut for later concatenation.
                    cut_lines.append( "file %s\n" % ( cut_video ) )
                else:
                    log.error( json.dumps( { 'album_uuid' : album_uuid, 
                                             'message'   : 'Something went wrong generating clip, output was: %s' % ( output ) } ) )
                    output_secs -= track_cut[1] - track_cut[0]
            
        except Exception as e:
            log.error( json.dumps( { 'album_uuid' : album_uuid, 
                                     'message'   : 'Unexpected error processing file %s: %s' % ( media_uuid, e ) } ) )
            # Note - we just keep going if we hit an error and hope for the best.

    # Open the output file for storing concatenation data.
    cut_file_name = '%s/cuts.txt' % ( workdir )
    cut_file = open( cut_file_name, 'w' )

    # DEBUG
    random.shuffle( cut_lines )
    if contact_id is None:
        random.shuffle( cut_lines )

    for line in cut_lines:
        cut_file.write( line )

    cut_file.close()

    if output_secs > min_output_secs:
        return ( True, album.title, output_secs )
    else:
        log.warning( json.dumps( { 'album_uuid' : album_uuid, 
                                   'message'   : 'Summary video length of %s was too short, returning False.' % ( output_secs ) } ) )
        return ( False, None, None )
                
def produce_summary_video( album_uuid, workdir, viblio_added_content_id, filename="Summary", title="A Gift from Viblio", output_secs=None ):
    # Open the output file for storing concatenation data.
    cut_file_name = '%s/cuts.txt' % ( workdir )
    output_file = '%s/summary.mp4' % ( workdir )

    if not os.path.isfile( cut_file_name ):
        raise Exception( "Couldn't find expected cut file at: %s" % ( cut_file_name ) )

    # DEBUG
    music_file = random.choice( glob.glob( '/wintmp/music/*m4a' ) )
    logo_file = '/wintmp/summary-test/logo.png'

    afade = ''
    if output_secs is not None:
        afade = '-af "afade=t=out:st=%s:d=5"' % ( output_secs - 5 )

    ffmpeg_opts = ' -filter_complex \'[2:0] split [a][b] ; [a] fade=out:st=3:duration=1, scale=-1:64 [c] ; [b] fade=in:st=%s:d=1, scale=-1:128 [d] ; [0:v][c] overlay=main_w-overlay_w-10:main_h-overlay_h-10 [x]; [x][d] overlay=trunc((main_w-overlay_w)/2):trunc((main_h-overlay_h)/2)\' ' % ( output_secs-1 )

    cmd = "ffmpeg -y -f concat -i %s -i %s -loop 1 -i %s -r 30000/1001 -c:a libfdk_aac %s %s -shortest %s" % ( cut_file_name, music_file, logo_file, afade, ffmpeg_opts, output_file )
    log.info( json.dumps( { 'album_uuid' : album_uuid, 
                            'message'   : 'Generating summary with command: %s' % ( cmd ) } ) )

    ( status, output ) = commands.getstatusoutput( cmd )

    if status != 0:
        message = "Error generating summary video: %s" % ( output )
        log.error( json.dumps( { 'album_uuid' : album_uuid, 
                                     'message'   : message } ) )
        raise Exception( message )
    else:


'''
        
def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

def run():
    try:
        sqs = __get_sqs().get_queue( config.album_summary_creation_queue )
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
        
        if 'action' not in options or options['action'] != 'create_video_summary':
            # This message is not for us, move on.
            message = None
            options = None
            return True;

        summary_types = [ 'moments' ]

        if 'summary_type' not in options or options['summary_type'] not in summary_types:
            # This message is not for us, move on.
            message = None
            options = None
            return True;

        # Mandatory options.
        # The UUID of the summary we will create.
        #summary_uuid = str( uuid.uuid4() )
        summary_uuid    = options['summary_uuid']
        user_uuid       = options['user_uuid']
        images          = options['images[]']
        summary_type    = options['summary_type']
        audio_track     = options['audio_track']

        if user_uuid is None or images is None or summary_type is None or audio_track is None:
            message = 'Error, empty input for one of user_uuid: %s, images: %s, summary_type: %s, and audio_track: %s' % ( user_uuid, images, summary_type, audio_track )
            log.error( json.dumps( { 'message' : message } ) )
            raise Exception( message )

        # Mandatory for some summary_types.
        contacts        = options.get( 'contacts[]', [] )
        videos          = options.get( 'videos[]', [] )
        
        # Optional, if set, store the result here.
        album_uuid      = options.get( 'album_uuid', None )

        # Optional controls for summary behavior.
        summary_style   = options.get( 'summary_style', 'classic' )
        order           = options.get( 'order', 'random' )
        effects         = options.get( 'effects[]', [] )
        moment_offsets  = options.get( 'moment_offsets[]', None )
        if moment_offsets is not None:
            moment_offsets = ( float( moment_offsets[0] ), float( moment_offsets[1] ) )
        else:
            moment_offsets = ( -2.5, 2.5 )
        target_duration = options.get( 'target_duration', None )
        if target_duration is not None:
            target_duration = float( target_duration )
        summary_options = options.get( 'summary_options', None )
        if summary_options is not None:
            try:
                summary_options = json.loads( summary_options )
            except Exception as e:
                log.error( json.dumps( { 'message' : "Error - summary_options JSON is malformed: %s" % ( e ) } ) )
                summary_options = {}
        else:
            summary_options = {}

        # Optional controls for summary metadata.
        title = options.get( 'title', '' )
        description     = options.get( 'description', '' )
        lat             = options.get( 'lat', None )
        if lat is not None:
            lat = float( lat )
        lng             = options.get( 'lng', None )
        if lng is not None:
            lng = float( lng )
        tags            = options.get( 'tags[]', [] )
        recording_date  = options.get( 'recording_date', datetime.datetime.now() )

        output_x        = options.get( 'output_x', 1280 )
        output_y        = options.get( 'output_y', 720 )

        workdir = config.faces_dir + '/album_summary/' + summary_uuid + '/'
        try:
            if not os.path.isdir( workdir ):
                os.makedirs( workdir )
        except Exception as e:
            log.error( json.dumps( { 'message' : "Error creating workdir %s: %s" % ( workdir, e ) } ) )
            raise

        # We need to delete the message here or it will reach its
        # visibility timeout and be processed again by other systems.
        # 
        # Summary creation is "best effort" in this regard - if we
        # fail we don't try again.
        sqs.delete_message( message )

        generate_summary( summary_type,
                          summary_uuid,
                          user_uuid,
                          images,
                          workdir,
                          audio_track,
                          contacts        = contacts,
                          videos          = videos,
                          album_uuid      = album_uuid,
                          summary_style   = summary_style,
                          order           = order,
                          effects         = effects,
                          moment_offsets  = moment_offsets,
                          target_duration = target_duration,
                          summary_options = summary_options,
                          title           = title,
                          description     = description,
                          lat             = lat,
                          lng             = lng,
                          tags            = tags,
                          recording_date  = recording_date,
                          output_x        = output_x,
                          output_y        = output_y )
                          
        log.info( json.dumps( { 'message' : "Completed successfully for summary_uuid: %s" % ( summary_uuid ) } ) )

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
