#!/usr/bin/env python

import commands
import datetime
import hashlib
import json
import logging
from logging import handlers
import math
import os
import pickle
import random
import re
import shutil
import tempfile
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'vsum: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

# DEBUG - fix this.
FFMPEG = 'ffmpeg'
FFMPEG = '/home/viblio/ffmpeg/git/ffmpeg/ffmpeg'

def distribute_clips( clips, windows, min_duration=None ):
    '''Distribute clips to windows.
    
    This attempts to place clips in the window whose aspect ratio is a
    close match for the clip, while also balancing the total content
    duration of the clips in the windows (note: this can be different
    from the total duration of the rendered window when cascading
    clips are used).

    If min_duration is != None, then the clips will continually be
    recycled until the min_duration is met.
    '''
    
    window_stats = []
    for window in windows:
        ar = float( window.width ) / window.height
        duration = 0
        window_stats.append( { 'window'   : window,
                               'ar'       : ar,
                               'duration' : duration } )

    def add_clips_helper():
        for clip in clips:
            ar = float( clip.video.width ) / clip.video.height
            duration = clip.get_duration()

            window_durations = [ x.compute_duration( x.clips ) for x in windows ]
            min_window_duration = min( window_durations )

            # Sort candidate windows by increasing AR match and then by increasing duration.
            window_stats.sort( key=lambda x: ( abs( x['ar'] - ar ), x['duration'] ) )
        
            # Find a window to add this clip to, while maintaining this
            # constraint:
            #
            # Find the first window sorted by closest aspect ratio and
            # then duration so long as adding this clip to the window so
            # long as:
            # window.duration + clip.duration > 2*(min_window_duration + clip.duration)
            # window.duration < min_duration
            clip_added = False
            for window in window_stats:
                if ( window['duration'] + duration ) <= 2*( min_window_duration + duration ):
                    if min_duration is None or window['duration'] < min_duration:
                        window['window'].clips.append( clip )
                        window['duration'] = window['window'].compute_duration( window['window'].clips )
                        print "Added %s to %s - duration is now: %s" % ( clip.label, window['window'].label, window['duration'] )
                        clip_added = True
                        break
                  
            if not clip_added and min_duration is None:
                raise Exception( "Failed to place clip %s in a window." % ( clip.label ) )

    if min_duration is None:
        add_clips_helper()
    else:
        add_clips_helper()
        window_durations = [ x.compute_duration( x.clips ) for x in windows ]
        while min( window_durations ) < min_duration:
            add_clips_helper()
            window_durations = [ x.compute_duration( x.clips ) for x in windows ]

# Some constants

# Clip display styles.
OVERLAY   = "overlay"
CROP      = "crop"
PAD       = "pad"
PAN       = "pan"
DISPLAY_STYLES = [ OVERLAY, CROP, PAD, PAN ]

# Overlay and pan directions directions
DOWN      = "down"  # Down and right are synonyms for pan directions.
LEFT      = "left"  # Left and up are synonyms for pan directions.
RIGHT     = "right" 
UP        = "up"    
STATIC    = "static"
OVERLAY_DIRECTIONS = [ DOWN, LEFT, RIGHT, UP, STATIC ]

# Pan directions
ALTERNATE = "alternate"
PAN_DIRECTIONS = [ ALTERNATE, DOWN, UP ]

class Display( object ):
    def __init__( self, 
                  overlay_concurrency = 4,
                  overlay_direction   = DOWN,
                  display_style       = PAD,
                  pan_direction       = ALTERNATE,
                  pad_bgcolor         = 'Black' ):
        '''
        display_style - How the clip will be rendered, defaults to PAD,
                        one of: OVERLAY, CROP, PAD, PAN

        pan_direction - If the clip is displayed with PAN display
                        style, and panning occurs, should it be from
                        the top/left to the bottom/right, the reverse,
                        or alternating.  Default is alternating.

        DEBUG - Document other options
        '''
        # This way of setting defaults allows the defaults to overlay to
        # callers who proxy the creation of this class.
        if overlay_concurrency is None:
            overlay_concurrency = 4
        if overlay_direction is None:
            overlay_direction = DOWN
        if display_style is None:
            display_style = PAN
        if pan_direction is None:
            pan_direction = ALTERNATE

        if display_style in DISPLAY_STYLES:
            self.display_style = display_style
        else:
            raise Exception( "Invalid display style: %s, valid display styles are: %s" % ( display_style, DISPLAY_STYLES ) )

        if overlay_direction in OVERLAY_DIRECTIONS:
            self.overlay_direction = overlay_direction
        else:
            raise Exception( "Invalid overlay direction: %s, valid overlay directions are: %s" % ( overlay_direction, OVERLAY_DIRECTIONS ) )

        if pan_direction == RIGHT:
            self.pan_direction = DOWN
        elif pan_direction == LEFT:
            self.pan_direction = UP
        elif pan_direction in PAN_DIRECTIONS:
            self.pan_direction = pan_direction
        else:
            raise Exception( "Invalid pan direction: %s, valid pan directions are: %s" % ( pan_direction, PAN_DIRECTIONS ) )

        self.prior_pan = UP
                         
        self.overlay_concurrency = overlay_concurrency

        self.pad_bgcolor = pad_bgcolor

    def get_pan_direction( self ):
        if self.pan_direction == ALTERNATE:
            if self.prior_pan == UP:
                self.prior_pan = DOWN
                return DOWN
            else:
                self.prior_pan = UP
                return UP
        else:
            self.prior_pan = self.pan_direction
            return self.pan_direction

def get_display( clip, window ):
    if clip.display is not None:
        return clip.display
    elif window.display is not None:
        return window.display
    else:
        return Display()

class Video( object ):
    # Class static variable so we only have to look things up once.
    videos = {}
    idx = 0

    def __init__( self, 
                  filename,
                  width=None,
                  height=None,
                  duration=None ):
        
        if not os.path.exists( filename ):
            raise Exception( "No video found at: %s" % ( filename ) )
        else:
            self.filename = filename

        self.label = "v%d" % ( Video.idx )
        Video.idx += 1

        if filename in Video.videos:
            self.width = Video.videos[filename][width]
            self.height = Video.videos[filename][height]
            self.duration = Video.videos[filename][duration]
        else:
            ( status, output ) = commands.getstatusoutput( "ffprobe -v quiet -print_format json -show_format -show_streams %s" % ( filename ) )
            info = json.loads( output )
            self.duration = float( info['format']['duration'] )
            self.width = int( info['streams'][0]['width'] )
            self.height = int( info['streams'][0]['height'] )
            Video.videos[filename] = { 'width'    : self.width,
                                       'height'   : self.height,
                                       'duration' : self.duration }
        
class Clip( object ):
    idx = 0

    def __init__( self,
                  video               = None,
                  start               = 0,
                  end                 = None,
                  display             = None,
                  clip           = None ):
        if video is None:
            raise Exception( "Clip consturctor requires either a video argument, or clone and clip arguments." )

        self.label = "c%d" % ( Clip.idx )
        Clip.idx += 1
            
        self.video = video
        
        self.start = start
            
        if end is None:
            self.end = video.duration
        else:
            self.end = end

        self.display = display
            
    def get_duration( self ):
        return self.end - self.start

# Note - I had intended to offer scale arguments for watermark, but
# ran across FFMPEG bugs (segmentation faults, memory corruption) when
# using the FFMPEG scale filter on PNG images, so I left it out.
class Watermark( object ):
    watermarks = {}
    idx = 0

    def __init__( self, 
                  filename,
                  x = "",
                  y = "",
                  fade_in_start = None,     # Negative values are taken relative to the end of the video
                  fade_in_duration = None,
                  fade_out_start = None,    # Negative values are taken relative to end of video.
                  fade_out_duration = None ):

        if not os.path.exists( filename ):
            raise Exception( "No watermark media found at: %s" % ( filename ) )
        else:
            self.filename = filename

        self.x = x
        self.y = y
        self.fade_in_start = fade_in_start
        self.fade_in_duration = fade_in_duration
        self.fade_out_start = fade_out_start
        self.fade_out_duration = fade_out_duration
        
        self.label = "w%d" % ( Watermark.idx )
        Watermark.idx += 1

        # We only store each watermark media input once no matter how
        # many times it is used.
        if filename not in Watermark.watermarks:
            Watermark.watermarks[filename] = True

class Window( object ):
    idx = 0
    z = 0
    layer_idx = 0
    prior_overlay = None
    tmpdir = '/tmp/vsum/'
    cache_dict_file = '/tmp/vsum/cachedb'
    cache_dict = {}

    @staticmethod
    def load_cache_dict():
        if os.path.exists( Window.cache_dict_file ):
            f = open( Window.cache_dict_file, 'r' )
            Window.cache_dict = pickle.load( f )
            f.close()
        else:
            if not os.path.isdir( Window.tmpdir ):
                os.makedirs( Window.tmpdir )
            Window.cache_dict = {}

    @staticmethod
    def save_cache_dict():
        if not os.path.isdir( Window.tmpdir ):
            os.makedirs( Window.tmpdir )

        f = open( Window.cache_dict_file, 'wb' )
        pickle.dump( Window.cache_dict, f )
        f.close()
    
    def __init__( self,
                  windows = None,
                  clips = None,
                  bgcolor = 'Black',
                  width = 1280,
                  height = 720,
                  # The position of this window relative to its parent
                  # window (if any)
                  x = 0,
                  y = 0,
                  duration = None, # The total rendered duration,
                                   # defaults to that of the audio
                                   # track. Short values may lead to
                                   # some clips never being visible,
                                   # long values may lead to empty
                                   # screen once all clips have been
                                   # shown.
                  z_index = None,
                  watermarks = None,
                  audio_filename = None,
                  display = None,
                  output_file = "./output.mp4",
                  overlay_batch_concurrency = 64 # The number of
                                                 # overlays that we
                                                 # will attempt to
                                                 # apply with one
                                                 # command line for
                                                 # FFMPEG - setting
                                                 # this higher may
                                                 # cause crashes and
                                                 # memory corruptions,
                                                 # setting it lower
                                                 # increases rendering
                                                 # time.
                  ):

        self.label = "w%d" % ( Window.idx )
        Window.idx += 1

        if windows is not None:
            self.windows = windows
        else:
            self.windows = []

        if clips is not None:
            self.clips = clips
        else:
            self.clips = []

        self.bgcolor  = bgcolor
        self.width    = width
        self.height   = height
        self.x        = x
        self.y        = y

        if z_index is not None:
            self.z_index = z_index
        else:
            self.z_index = Window.z
            Window.z += 1
        
        if watermarks is not None:
            self.watermarks = watermarks
        else:
            self.watermarks = []

        if audio_filename is not None:
            if not os.path.exists( audio_filename ):
                raise Exception( "No audio found at: %s" % ( audio_filename ) )
            else:
                self.audio_filename = audio_filename
                ( status, output ) = commands.getstatusoutput( "ffprobe -v quiet -print_format json -show_format %s" % ( audio_filename ) )
                audio_info = json.loads( output )
                self.audio_duration = float( audio_info['format']['duration'] )
        else:
            self.audio_filename = None
            self.audio_duration = None

        if duration is None and audio_filename is not None:
            self.duration = self.audio_duration
        else:
            self.duration = duration

        if display is not None:
            self.display = display
        else:
            self.display = Display()

        self.overlay_completions = []
        self.overlay_filled = False
        
        Window.prior_overlay = None

        if Window.cache_dict == {}:
            Window.load_cache_dict()

        self.outputfile = output_file
        
        self.overlay_batch_concurrency = overlay_batch_concurrency

    def get_next_renderfile( self ):
        return "%s/%s.mp4" % ( Window.tmpdir, str( uuid.uuid4() ) )

    def render( self, helper=False ):
        # File to accumulate things in.
        tmpfile = self.get_next_renderfile()

        # Handle the case where there are no clips
        if len( self.clips ) == 0:
            cmd = '%s -y -r 30000/1001 -q:v 1 -filter_complex " color=%s:size=%dx%d " -t %f %s' % ( FFMPEG, self.bgcolor, self.width, self.height, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( tmpfile, cmd ) )
        else:
            tmpfile = self.render_clips( self.clips )

        for window in sorted( self.windows, key=lambda x: x.z_index ):
            if window.duration is None:
                window.duration = self.duration
            current = tmpfile
            window_file = window.render( helper=True )
            tmpfile = self.get_next_renderfile()

            cmd = '%s -y -i %s -i %s -r 30000/1001 -q:v 1 -filter_complex " [0:v] [1:v] overlay=x=%s:y=%s:eof_action=pass " -t %f %s' % ( FFMPEG, current, window_file, window.x, window.y, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error applying overlay window %s to file %s with command: %s" % ( window_file, current, cmd ) )

        # DEBUG - rewrite add_watermarks.
        #self.add_watermarks()

        if self.audio_filename:
            if self.audio_duration is not None and self.audio_duration == self.duration:
                audio_fade_start = self.duration
                audio_fade_duration = 0
            else:
                audio_fade_start = max( 0, self.duration - 5 )
                audio_fade_duration = self.duration - audio_fade_start
            # DEBUG - remove strict.
            afade_clause = ' -strict -2 -af "afade=t=out:st=%f:d=%f" ' % ( audio_fade_start, audio_fade_duration )
            current = tmpfile
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -i %s -i %s -vf copy %s -t %f %s' % ( FFMPEG, current, self.audio_filename, afade_clause, self.duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error adding audio %s to file %s with command: %s" % ( self.audio_filename, current, cmd ) )

        if not helper:
            shutil.copyfile( tmpfile, self.outputfile )
        return tmpfile

    def add_watermarks( self ):
        cmd = ""

        for watermark in self.watermarks:

            fade_clause = ""
            if watermark.fade_in_start is not None:
                in_start = watermark.fade_in_start
                if in_start < 0:
                    in_start = self.duration + in_start
                in_duration = min( watermark.fade_in_duration, self.duration - in_start )
                fade_clause = "fade=in:st=%f:d=%f" % ( in_start, in_duration )
            if watermark.fade_out_start is not None:
                out_start = watermark.fade_out_start
                if out_start < 0:
                    out_start = self.duration + out_start
                out_duration = min( watermark.fade_out_duration, self.duration - out_start )
                if fade_clause == "":
                    fade_clause = "fade="
                else:
                    fade_clause += ":"
                fade_clause += "out:st=%f:d=%f" % ( out_start, out_duration )

            mark_clause = fade_clause
            if mark_clause == "":
                mark_clause = "copy"

            cmd += " [%s] %s [%s] ; " % ( Window.media_inputs[watermark.filename], mark_clause, watermark.label )

        # Overlay them onto one another
        if not Window.prior_overlay:
            Window.prior_overlay = 'base_%s' % ( self.label )
        for watermark in self.watermarks:
            cmd += ' [%s] [%s] overlay=x=%s:y=%s:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, watermark.label, watermark.x, watermark.y, Window.layer_idx )
            Window.prior_overlay = 'o%d' % ( Window.layer_idx )
            Window.layer_idx += 1

        return cmd

    def get_clip_hash( self, clip, width, height, pan_direction="" ):
        display = get_display( clip, self )
        clip_name = "%s%s%s%s%s%s%s" % ( os.path.abspath( clip.video.filename ), 
                                         clip.start, 
                                         clip.end, 
                                         display.display_style, 
                                         width, 
                                         height, 
                                         pan_direction )
        md5 = hashlib.md5()
        md5.update( clip_name )
        return md5.hexdigest()

    def render_clips( self, clips ):
        # For each clip we:
        #
        # 1. Check in our cache to see if we already have a version of
        # this clip in the appropriate resolution.
        #
        # 2. If there is a cache miss, produce a clip of the
        # appropriate resolution and cache it.
        #
        # 3. Concatenate all the resulting clips.

        if len( clips ) == 0:
            # Nothing to do.
            return

        clip_files = []
        overlays = []
        
        # Build up our library of clips.
        for clip in self.clips:
            filename = self.clip_render( clip )

            display = get_display( clip, self )
            if display.display_style == OVERLAY:
                overlays.append( { 'clip' : clip,
                                   'filename' : filename } )
            else:
                clip_files.append( filename )
        
        # Concatenate all clip files.
        if len( clip_files ):
            tmpfile = self.get_next_renderfile()
            concat_file = "%s/concat-%s.txt" % ( Window.tmpdir, str( uuid.uuid4() ) )
            f = open( concat_file, 'w' )
            for clip_file in clip_files:
                f.write( "file '%s'\n" % ( clip_file ))
            f.close()
            cmd = "%s -y -f concat -i %s -q:v 1 -an %s" % ( FFMPEG, concat_file, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing concatenated file %s with command: %s" % ( tmpfile, cmd ) )
        else:
            # All the clips are overlays - build a background for the clips.
            duration = self.compute_duration( self.clips )
            tmpfile = self.get_next_renderfile()
            cmd = '%s -y -r 30000/1001 -q:v 1 -filter_complex " color=%s:size=%dx%d " -t %f %s' % ( FFMPEG, self.bgcolor, self.width, self.height, duration, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( tmpfile ):
                raise Exception( "Error producing solid background file %s with command: %s" % ( tmpfile, cmd ) )   

        # Add our overlays.
        ( duration, overlay_timing ) = self.compute_duration( clips, include_overlay_timing=True )
        for overlay_group in range( 0, len( overlays ), self.overlay_batch_concurrency ):
            Window.prior_overlay = '0:v'
            cmd = "%s -y -i %s " % ( FFMPEG, tmpfile )
            include_clause = ""
            scale_clause = ""
            filter_complex = ' -r 30001/1001 -q:v 1 -filter_complex " '
            for overlay_idx in range( overlay_group, min( len( overlays ), overlay_group + self.overlay_batch_concurrency ) ):
                overlay_start = overlay_timing[overlay_idx][0]
                overlay_end = overlay_timing[overlay_idx][1]
                overlay = overlays[overlay_idx]['clip']
                display = get_display( overlay, self )
                filename = overlays[overlay_idx]['filename']

                include_clause += " -i %s " % ( filename )

                scale = random.uniform( 1.0/2, 1.0/6 )
                # Set the width to be randomly between 1/2 and 1/6th
                # of the window width, and the height so the aspect
                # ratio is retained.
                ow = 2*int( self.width*scale / 2 )
                oh = 2*int( overlay.video.height * ow / ( overlay.video.width * 2 ) )
                ilabel = overlay_idx + 1 - overlay_group
                filter_complex += " [%d:v] scale=width=%d:height=%d,setpts=PTS-STARTPTS+%f/TB [o%d] ; " % ( ilabel, ow, oh, overlay_start, overlay_idx )

                direction = display.overlay_direction

                if direction in [ UP, DOWN ]:
                    x = random.randint( 0, self.width - ow )
                    if direction == UP:
                        y = "'if( gte(t,%d), H-(t-%d)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.height+oh ) / overlay.get_duration() )
                    elif direction == DOWN:
                        y = "'if( gte(t,%d), -h+(t-%d)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.height+oh ) / overlay.get_duration() )
                else:
                    y = random.randint( 0, self.height - oh )
                    if direction == LEFT:
                        x = "'if( gte(t,%d), -w+(t-%d)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.width+ow ) / overlay.get_duration() )
                    elif direction == RIGHT:
                        x = "'if( gte(t,%d), W-(t-%d)*%f, NAN)'" % ( overlay_start, overlay_start, float( self.width+ow ) / overlay.get_duration() )

                filter_complex += ' [%s] [o%d] overlay=x=%s:y=%s:eof_action=pass [t%s] ; ' % ( Window.prior_overlay, overlay_idx, x, y, Window.layer_idx )
                Window.prior_overlay = 't%d' % ( Window.layer_idx )
                Window.layer_idx += 1

                print "group, idx: %s, %s" % ( overlay_group, overlay_idx )

            tmpfile = self.get_next_renderfile()                                          
            cmd += include_clause + filter_complex + ' [t%s] copy " %s' % ( Window.layer_idx - 1, tmpfile )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status != 0 or not os.path.exists( filename ):
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, filename ) )

        return tmpfile

        # Overlay overlays in batches.

        '''
            clip_hash = self.get_clip_hash( clip )
            
            ilabel = Window.media_inputs[clip.video.filename]
            olabel = clip.label

            display = get_display( clip, self )

            # Compute the PST offset for this clip.
            if display.display_style != OVERLAY:
                clip.pts_offset = pts_offset
                pts_offset += clip.get_duration()
                if pts_offset > self.current_duration:
                    self.current_duration = pts_offset
            else:
                # It's complicated if this is a cascading clip.
                if len( self.overlay_completions ) < display.overlay_concurrency:
                    if self.overlay_filled:
                        clip.pts_offset = min( self.overlay_completions )
                    else:
                        clip.pts_offset = 0
                    self.overlay_completions.append( clip.pts_offset + clip.get_duration() )
                    if len( self.overlay_completions ) == display.overlay_concurrency:
                        self.overlay_filled = True
                else:
                    # Determine when we can begin the next overlay.
                    clip.pts_offset = min( self.overlay_completions )
                    # Remove clips that will end at that offset.
                    while self.overlay_completions.count( clip.pts_offset ):
                        self.overlay_completions.remove( clip.pts_offset )
                    self.overlay_completions.append( clip.pts_offset + clip.get_duration() )
                if max( self.overlay_completions ) > self.current_duration:
                    self.current_duration = max( self.overlay_completions )

            scale_clause = clip.get_scale_clause( self )

            cmd += ' [%s] trim=start=%s:end=%s:duration=%s,setpts=PTS-STARTPTS+%s/TB,%s [%s] ; ' % ( ilabel, clip.start, clip.end, clip.get_duration(), clip.pts_offset, scale_clause, olabel )
            
            thing = 'ffmpeg -i %s -filter_complex " trim=start=%f:end=%f:duration=%f,setpts=PTS-STARTPTS+%s/TB,%s " %s/%s.mp4' % ( clip.video.filename, clip.start, clip.end, clip.get_duration(), clip.pts_offset, scale_clause, workdir, olabel )
            print thing

        # Overlay them onto one another
        if not Window.prior_overlay:
            Window.prior_overlay = 'base_%s' % ( self.label )

        # Build up a render for this window only.
        for idx, clip in enumerate( self.clips ):
            display = get_display( clip, self )

            if display.display_style != OVERLAY:
                cmd += ' [%s] [%s] overlay=x=%d:y=%d:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, clip.label, self.x, self.y, Window.layer_idx )
            else:
                direction = display.overlay_direction

                if direction in [ UP, DOWN ]:
                    x = self.x + random.randint( 0, self.width - clip.width )
                    if direction == UP:
                        y = "'%d + if( gte(t,%d), H-(t-%d)*%f, NAN)'" % ( self.y, clip.pts_offset, clip.pts_offset, float( self.height+clip.height ) / clip.get_duration() )
                    elif direction == DOWN:
                        y = "'%d + if( gte(t,%d), -h+(t-%d)*%f, NAN)'" % ( self.y, clip.pts_offset, clip.pts_offset, float( self.height+clip.height ) / clip.get_duration() )
                else:
                    y = self.y + random.randint( 0, self.height - clip.height )
                    if direction == LEFT:
                        x = "'%d + if( gte(t,%d), -w+(t-%d)*%f, NAN)'" % ( self.x, clip.pts_offset, clip.pts_offset, float( self.width+clip.width ) / clip.get_duration() )
                    elif direction == RIGHT:
                        x = "'%d + if( gte(t,%d), W-(t-%d)*%f, NAN)'" % ( self.x, clip.pts_offset, clip.pts_offset, float( self.width+clip.width ) / clip.get_duration() )

                cmd += ' [%s] [%s] overlay=x=%s:y=%s:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, clip.label, x, y, Window.layer_idx )
            Window.prior_overlay = 'o%d' % ( Window.layer_idx )
            Window.layer_idx += 1
            '''

    def clip_render( self, clip ):
        display = get_display( clip, self )

        scale_clause = ""
        clip_width = None
        clip_height = None

        if display.display_style == PAD:
            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, min )

            clip_width = ow
            clip_height = oh

            xterm = ""
            if ow != self.width:
                xterm = ":x=%d" % ( ( self.width - ow ) / 2 )

            yterm = ""
            if oh != self.height:
                yterm = ":y=%s" % ( ( self.height - oh ) / 2 )

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
            
            scale_clause += "pad=width=%d:height=%d%s%s:color=%s" % ( self.width, self.height, xterm, yterm, display.pad_bgcolor )

        elif display.display_style == CROP:
            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, max )

            clip_width = ow
            clip_height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
                
            scale_clause += "crop=w=%d:h=%d" % ( self.width, self.height )

        elif display.display_style == PAN:
            import pdb
            #pdb.set_trace()

            ( scale, ow, oh ) = self.get_output_dimensions( clip.video.width, clip.video.height, self.width, self.height, max )

            clip_width = ow
            clip_height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )

            # We need to pan the image if scale != 1.
            pan_clause = ''
            if ow > self.width or oh > self.height:
                # Note - we only want to call this if we're actually
                # panning, or it will erroneously trigger us to
                # alternate pan directions.
                direction = display.get_pan_direction() 

                xpan = ''
                if ow  > self.width:
                    xpan = "x=%s" % ( self.get_pan_clause( clip, direction, ow, self.width ) )

                ypan = ''
                if oh  > self.height:
                    ypan = "y=%s" % ( self.get_pan_clause( clip, direction, oh, self.height ) )

                # NOTE: This logic does not allow both x and y
                # panning, additional stuff would be required to get
                # the : seperators right in the pan clause if both
                # could be present.
                pan_clause = ":%s%s" % ( xpan, ypan )

            scale_clause += 'crop=w=%d:h=%d%s' % ( self.width, self.height, pan_clause )

        elif display.display_style == OVERLAY:
            # Ovarlays will be scaled at the time the overlay is
            # applied so we can reuse the same clips at different
            # scales.
            scale_clause = ""

            clip_width = clip.video.width
            clip_height = clip.video.height

        else:
            raise Exception( "Error, unknown display style: %s" % ( display.display_style ) )

        if scale_clause != "":
            scale_clause = ' -filter_complex " %s " ' % ( scale_clause )

        # Now that we have our scale clause, render this thing.
         
        # Check the cache for such a clip.
        # If not, produce it and save it in the cache.
        clip_hash = self.get_clip_hash( clip, self.width, self.height, display.prior_pan ) 
        if clip_hash in Window.cache_dict:
            print "Cache hit for clip: %s" % ( clip_hash )
            return Window.cache_dict[clip_hash]
        else:
            filename = "%s/%s.mp4" % ( Window.tmpdir, clip_hash )
            
            cmd = '%s -y -ss %f -i %s -r 30000/1001 -q:v 1 -an %s -t %f %s' % ( FFMPEG, clip.start, clip.video.filename, scale_clause, clip.get_duration(), filename )
            print "Running: %s" % ( cmd )
            ( status, output ) = commands.getstatusoutput( cmd )
            print "Output was: %s" % ( output )
            if status == 0 and os.path.exists( filename ):
                Window.cache_dict[clip_hash] = filename
                Window.save_cache_dict()
            else:
                raise Exception( "Error producing clip file by %s at: %s" % ( cmd, filename ) )

        return filename

    def get_pan_clause( self, clip, direction, c, w ):
        duration = clip.get_duration()
        pan_clause = ''
        if c  > w:
            pixels_per_sec = float( ( c - w ) ) / duration
            if direction in [ DOWN, RIGHT ]:
                pan_clause = "trunc(%f * t)" % ( pixels_per_sec )
            elif direction in [ UP, LEFT ]:
                pan_clause = "%d-trunc(%f * t)" % ( c - w, pixels_per_sec )
            else:
                raise Exception( "Could not determine pan direction." )
            
        return pan_clause

    def get_output_dimensions( self, cw, ch, ww, wh, operator ):
        scale = operator( float( ww ) / cw, float( wh ) / ch )
        ow = int( cw * scale )
        oh = int( ch * scale )
        
        # If we are very near the aspect ratio of the target
        # window snap to that ratio.
        if ( ow > ww - 2 ) and ( ow < ww + 2 ):
            ow = ww
        if ( oh > wh - 2 ) and ( oh < wh + 2 ):
            oh = wh
            
        # If we have an odd size add 1.
        if ow % 2:
            ow += 1
        if oh %2:
            oh += 1

        return ( scale, ow, oh )

    def compute_duration( self, clips, include_overlay_timing=False ):
        '''Don't actually do anything, just report how long the clips will
        take to render in this window.
        
        Returns either a float (if include_overlay_timing is false), or
        a tuple with the float and an array of overlay timing data.

        The array of timing data has N elements, one for each clip of
        type Overlay, and each element is a start time, end time
        tuple.
        '''

        duration = 0
        pts_offset = 0
        overlay_completions = []
        overlay_filled = False
        overlay_timing = []
        for clip in clips:
            display = get_display( clip, self )

            # Compute the PST offset for this clip.
            if display.display_style != OVERLAY:
                pts_offset += clip.get_duration()
                if pts_offset > duration:
                    duration = pts_offset
            else:
                # It's complicated if this is a cascading clip.
                overlay_pts_offset = 0
                if len( overlay_completions ) < display.overlay_concurrency:
                    if overlay_filled:
                        if len( overlay_completions ):
                            overlay_pts_offset = min( overlay_completions )
                    else:
                        overlay_pts_offset = 0
                    overlay_completions.append( overlay_pts_offset + clip.get_duration() )
                    overlay_timing.append( ( overlay_pts_offset, overlay_pts_offset + clip.get_duration() ) )
                    if len( overlay_completions ) == display.overlay_concurrency:
                        overlay_filled = True
                else:
                    # Determine when we can begin the next overlay.
                    overlay_pts_offset = min( overlay_completions )
                    # Remove clips that will end at that offset.
                    while overlay_completions.count( overlay_pts_offset ):
                        overlay_completions.remove( overlay_pts_offset )
                    overlay_completions.append( overlay_pts_offset + clip.get_duration() )
                    overlay_timing.append( ( overlay_pts_offset, overlay_pts_offset + clip.get_duration() ) )
                if max( [ x[1] for x in overlay_timing ] ) > duration:
                    duration = max( [ x[1] for x in overlay_timing ] )
                    
        if include_overlay_timing:
            return ( duration, overlay_timing )
        else:
            return duration

if __name__ == '__main__':
    # Future features / debugging
    # * [Parsed_overlay_31 @ 0x1da5180] [framesync @ 0x1da5d68] Buffer queue overflow, dropping.

    # OK, we have the following problems:
    # 1. The command line gets super long, and may exceed limits.
    # 2. With so many streams we run into performance problems.
    #
    # Alternate approach:
    # Build each window seperately in a seperate file.
    # "Loop" by concatenating multiple inputs of the seperate files.
    # ?? Maybe building each clip into its own file in a work dir?

    # * Bad behavior can occur when a single clip is rendered multiple
    #   times due to its state.

    # This much is basically working.
    d = Display( display_style = PAN )

    #m1 = Watermark( '/wintmp/summary-test/logo.png',
    #                x = "main_w-overlay_w-10",
    #                y = "main_h-overlay_h-10",
    #                fade_out_start = 3,
    #                fade_out_duration = 1 )
    #m2 = Watermark( '/wintmp/summary-test/logo128.png',
    #                x = "trunc((main_w-overlay_w)/2)",
    #                y = "trunc((main_h-overlay_h)/2)",
    #                fade_in_start = -1,
    #                fade_in_duration = 1 )

    w0 = Window( width=1280, height=1024, audio_filename='/wintmp/music/human405.m4a' )
    w1 = Window( display = d, height=1024, width=720 )
    w2 = Window( width=200, height=200, x=520, y=520 )
    w3 = Window( display=Display( display_style=OVERLAY, overlay_direction=RIGHT ), bgcolor='White', width=560, height=512, x=720 )
    #w3 = Window( display=Display( display_style=OVERLAY, overlay_direction=RIGHT ), bgcolor='White', width=560, height=512, x=720, audio_filename='/wintmp/music/human405.m4a' )
    w4 = Window( display=Display( display_style=PAD, overlay_direction=RIGHT, pad_bgcolor='Green' ), bgcolor='Green', width=560, height=512, x=720, y=512 )
    v1 = Video( 'test.mp4' )
    v2 = Video( 'flip.mp4' )    

    #w0.watermarks = [ m1, m2 ]

    c1 = Clip( v1, 1, 3 )  
    c2 = Clip( v1, 7, 8 )
    c3 = Clip( v2, 5, 6 )
    cx = Clip( v1, 4, 9 )
    c4 = Clip( v1, 4, 9, display=Display( display_style=OVERLAY, overlay_direction = UP ) )
    c5 = Clip( v2, 0, 1, display=Display( display_style=OVERLAY, overlay_direction = DOWN ) )
    c6 = Clip( v2, 1, 2, display=Display( display_style=OVERLAY, overlay_direction = LEFT ) )
    c7 = Clip( v2, 2, 3, display=Display( display_style=OVERLAY, overlay_direction = RIGHT ) )
    c8 = Clip( v2, 3, 5 )

    #w0.windows = [ w2 ]
    #w0.clips = [ cx ]
    #w2.clips = [ c2 ]
    #print w0.render()

    w1.windows = [ w2 ]
    w0.windows = [ w1, w3, w4 ]

    if 0:
        w2.clips = [ c3 ]
        w1.clips = [ c1, c2 ]
        w3.clips = [ c4, c5, c6, c7, c8 ]
    else:
        distribute_clips( [ c1, c2, c3, c8, cx, c4, c5, c6, c7 ], [ w1, w2, w3, w4 ], w0.duration )
        #distribute_clips( [ c1, c2, c3, c8, cx, c4, c5, c6, c7 ], [ w3 ], w3.duration )


    result = w0.render()
    print result
    #result = w0.render()
    #print result
    
        
        

    
