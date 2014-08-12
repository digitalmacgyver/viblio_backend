#!/usr/bin/env python

import commands
import datetime
import json
import logging
from logging import handlers
import math
import os
import random
import re
import time

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

    def add_clips_helper( clone = False ):
        for orig_clip in clips:
            if clone:
                clip = Clip( clone=True, clip=orig_clip )
            else:
                clip = orig_clip
                
            ar = float( clip.video.width ) / clip.video.height
            duration = clip.get_duration()

            window_durations = [ compute_window_duration( x.clips, x ) for x in windows ]
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
                        window['duration'] = compute_window_duration( window['window'].clips, window['window'] )
                        clip_added = True
                        break
                  
            if not clip_added and min_duration is None:
                raise Exception( "Failed to place clip %s in a window." % ( clip.label ) )

    if min_duration is None:
        add_clips_helper()
    else:
        add_clips_helper()
        window_durations = [ compute_window_duration( x.clips, x ) for x in windows ]
        while min( window_durations ) < min_duration:
            window_durations = [ compute_window_duration( x.clips, x ) for x in windows ]
            add_clips_helper( clone = True )

def compute_window_duration( clips, window, cascade_concurrency=None ):
    '''Don't actually do anything, just report how long the clips will
    take to render in this window.'''

    duration = 0
    pts_offset = 0
    cascade_completions = []
    cascade_filled = False
    for clip in clips:
        display = get_display( clip, window )

        # Compute the PST offset for this clip.
        if display.display_style != CASCADE:
            pts_offset += clip.get_duration()
            if pts_offset > duration:
                duration = pts_offset
        else:
            # It's complicated if this is a cascading clip.
            cascade_pts_offset = 0
            if len( cascade_completions ) < display.cascade_concurrency:
                if cascade_filled:
                    cascade_pts_offset = min( cascade_completions )
                else:
                    cascade_pts_offset = 0
                cascade_completions.append( cascade_pts_offset + clip.get_duration() )
                if len( cascade_completions ) == display.cascade_concurrency:
                    cascade_filled = True
            else:
                # Determine when we can begin the next cascade.
                cascade_pts_offset = min( cascade_completions )
                # Remove clips that will end at that offset.
                while cascade_completions.count( cascade_pts_offset ):
                    cascade_completions.remove( cascade_pts_offset )
                cascade_completions.append( cascade_pts_offset + clip.get_duration() )
            if max( cascade_completions ) > duration:
                duration = max( cascade_completions )

    return duration

# Some constants

# Clip display styles.
CASCADE   = "cascade"
CROP      = "crop"
PAD       = "pad"
PAN       = "pan"
DISPLAY_STYLES = [ CASCADE, CROP, PAD, PAN ]

# Cascade and pan directions directions
DOWN      = "down"  # Down and right are synonyms for pan directions.
LEFT      = "left"  # Left and up are synonyms for pan directions.
RIGHT     = "right" 
UP        = "up"    
CASCADE_DIRECTIONS = [ DOWN, LEFT, RIGHT, UP ]

# Pan directions
ALTERNATE = "alternate"
PAN_DIRECTIONS = [ ALTERNATE, DOWN, UP ]

class Display( object ):
    def __init__( self, 
                  cascade_concurrency = 4,
                  cascade_direction   = DOWN,
                  display_style       = PAD,
                  pan_direction       = ALTERNATE,
                  pad_bgcolor         = 'Black' ):
        '''
        display_style - How the clip will be rendered, defaults to PAD,
                        one of: CASCADE, CROP, PAD, PAN

        pan_direction - If the clip is displayed with PAN display
                        style, and panning occurs, should it be from
                        the top/left to the bottom/right, the reverse,
                        or alternating.  Default is alternating.

        DEBUG - Document other options
        '''
        # This way of setting defaults allows the defaults to cascade to
        # callers who proxy the creation of this class.
        if cascade_concurrency is None:
            cascade_concurrency = 4
        if cascade_direction is None:
            cascade_direction = DOWN
        if display_style is None:
            display_style = PAN
        if pan_direction is None:
            pan_direction = ALTERNATE

        if display_style in DISPLAY_STYLES:
            self.display_style = display_style
        else:
            raise Exception( "Invalid display style: %s, valid display styles are: %s" % ( display_style, DISPLAY_STYLES ) )

        if cascade_direction in CASCADE_DIRECTIONS:
            self.cascade_direction = cascade_direction
        else:
            raise Exception( "Invalid cascade direction: %s, valid cascade directions are: %s" % ( cascade_direction, CASCADE_DIRECTIONS ) )

        if pan_direction == RIGHT:
            self.pan_direction = DOWN
        elif pan_direction == LEFT:
            self.pan_direction = UP
        elif pan_direction in PAN_DIRECTIONS:
            self.pan_direction = pan_direction
        else:
            raise Exception( "Invalid pan direction: %s, valid pan directions are: %s" % ( pan_direction, PAN_DIRECTIONS ) )

        self.prior_pan = UP
                         
        self.cascade_concurrency = cascade_concurrency

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
            self.duration = info['format']['duration']
            self.width = info['streams'][0]['width']
            self.height = info['streams'][0]['height']
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
                  clone               = False,
                  clip           = None ):
        if not clone:
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
            
            self.pts_offset = 0
            
            self.width = None
            self.height = None
        else:
            if clip is not None:
                self.clone( clip )
            else:
                raise Exception( "Must provide clip argument if clone is true." )
        
    def clone( self, clip ):
        self.label = "c%d" % ( Clip.idx )
        Clip.idx += 1
        
        self.video = clip.video
        self.start = clip.start
        self.end = clip.end
        self.display = clip.display

        # These fields are calculated for the object during rendinging
        # in a window, so we don't clone them.
        self.pts_offset = 0
        self.width = None
        self.height = None

    def get_duration( self ):
        return self.end - self.start

    def get_scale_clause( self, window ):
        display = get_display( self, window )

        if display.display_style == PAD:
            ( scale, ow, oh ) = self.get_output_dimensions( self.video.width, self.video.height, window.width, window.height, min )
            self.width = ow
            self.height = oh

            xterm = ""
            if ow != window.width:
                xterm = ":x=%d" % ( ( window.width - ow ) / 2 )

            yterm = ""
            if oh != window.height:
                yterm = ":y=%s" % ( ( window.height - oh ) / 2 )

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
            
            scale_clause += "pad=width=%d:height=%d%s%s:color=%s" % ( window.width, window.height, xterm, yterm, display.pad_bgcolor )
        elif display.display_style == CROP:
            ( scale, ow, oh ) = self.get_output_dimensions( self.video.width, self.video.height, window.width, window.height, max )
            self.width = ow
            self.height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
                
            scale_clause += "crop=w=%d:h=%d" % ( window.width, window.height )

        elif display.display_style == PAN:
            ( scale, ow, oh ) = self.get_output_dimensions( self.video.width, self.video.height, window.width, window.height, max )
            self.width = ow
            self.height = oh

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
    

            # We need to pan the image if scale != 1.
            pan_clause = ''
            if ow > window.width or oh > window.height:
                # Note - we only want to call this if we're actually
                # panning, or it will erroneously trigger us to
                # alternate pan directions.
                direction = display.get_pan_direction() 

                xpan = ''
                if ow  > window.width:
                    xpan = "x=%s" % ( self.get_pan_clause( direction, ow, window.width ) )

                ypan = ''
                if oh  > window.height:
                    ypan = "y=%s" % ( self.get_pan_clause( direction, oh, window.height ) )

                # NOTE: This logic does not allow both x and y
                # panning, additional stuff would be required to get
                # the :'s right in the pan clause if both could be
                # present.
                pan_clause = ":%s%s" % ( xpan, ypan )

            scale_clause += "crop=w=%d:h=%d%s" % ( window.width, window.height, pan_clause )

        elif display.display_style == CASCADE:
                scale = random.uniform( 1.0/2, 1.0/6 )
                # Set the width to be randomly between 1/2 and 1/6th
                # of the window width, and the height so the aspect
                # ratio is retained.
                ow = 2*int( window.width*scale / 2 )
                oh = 2*int( self.video.height * ow / ( self.video.width * 2 ) )
                self.width = ow
                self.height = oh

                scale_clause = "scale=width=%d:height=%d" % ( ow, oh )
        else:
            raise Exception( "Error, unknown display style: %s" % ( display.display_style ) )

        return scale_clause

    def get_pan_clause( self, direction, c, w ):
        duration = self.get_duration()
        pan_clause = ''
        if c  > w:
            pixels_per_sec = float( ( c - w ) ) / duration
            if direction in [ DOWN, RIGHT ]:
                pan_clause = "trunc(%f * ( t - %f ) )" % ( pixels_per_sec, self.pts_offset )
            elif direction in [ UP, LEFT ]:
                pan_clause = "%d-trunc(%f * ( t - %f ) )" % ( c - w, pixels_per_sec, self.pts_offset )
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
    media_inputs = {}
    layer_idx = 0
    prior_overlay = None
    target_duration = None

    def __init__( self,
                  windows = None,
                  clips = None,
                  bgcolor = 'Black',
                  width = 1280,
                  height = 720,
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
                  display = None ):

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
            self.audio_duration = None

        if duration is None and audio_filename is not None:
            self.duration = self.audio_duration
        else:
            self.duration = duration

        if display is not None:
            self.display = display
        else:
            self.display = Display()

        self.cascade_completions = []
        self.cascade_filled = False
        
        self.current_duration = None

        Window.prior_overlay = None

    def render( self ):
        #import pdb
        #pdb.set_trace()

        if len( self.windows ) == 0 and len( self.clips ) == 0:
            raise Exception( "Can't render with no clips and no child windows." )

        cmd = '%s -y -r 30000/1001 ' % ( FFMPEG )
        for idx, video in enumerate( sorted( Video.videos.keys() ) ):
            cmd += " -i %s " % ( video )
            Window.media_inputs[video] = '%d:v' % ( idx )

        for idx, watermark_filename in enumerate( Watermark.watermarks.keys() ):
            cmd += " -loop 1 -i %s " % ( watermark_filename )
            Window.media_inputs[watermark_filename] = '%d:0' % ( len( Video.videos.keys() ) + idx )

        # DEBUG - get libfdk_aac working with new ffmpeg, or fix buffer overflow problems.
        #cmd += " -i %s -c:a libfdk_aac " % ( self.audio_filename )
        cmd += " -i %s " % ( self.audio_filename )
        Window.media_inputs[self.audio_filename] = '%d:a' % ( len( Video.videos.keys() ) + len( Watermark.watermarks.keys() ) )
            
        cmd += ' -filter_complex " color=%s:size=%sx%s [base_%s] ; ' % ( self.bgcolor, self.width, self.height, self.label )

        cmd += self.render_window()

        cmd += self.add_watermarks()

        if self.audio_duration is not None and self.audio_duration == self.duration:
            audio_fade_start = self.duration
            audio_fade_duration = 0
        else:
            audio_fade_start = max( 0, self.duration - 5 )
            audio_fade_duration = self.duration - audio_fade_start

        afade_clause = "afade=t=out:st=%f:d=%f" % ( audio_fade_start, audio_fade_duration )

        return cmd + ' [%s] %s [audio] " -map [%s] -map [audio] -t %f -strict -2 output.mp4' % ( Window.media_inputs[self.audio_filename], afade_clause, Window.prior_overlay, self.duration )

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

    def render_window( self ):
        # We render clips first, then windows on top of them.
        cmd = self.add_clips( self.clips )

        # Then we recursively descend into our child windows.
        for window in sorted( self.windows, key=lambda x: x.z_index ):
            # DEBUG - cmd += window.render_window()
            print window.render_window()

        #import pdb
        #pdb.set_trace()
        return cmd

    def add_clips( self, clips ):
        '''Where the magic happens.'''

        # Build up our library of clips.
        cmd = ''
        pts_offset = 0
        for clip in self.clips:
            ilabel = Window.media_inputs[clip.video.filename]
            olabel = clip.label

            display = get_display( clip, self )

            # Compute the PST offset for this clip.
            if display.display_style != CASCADE:
                clip.pts_offset = pts_offset
                pts_offset += clip.get_duration()
                if pts_offset > self.current_duration:
                    self.current_duration = pts_offset
            else:
                # It's complicated if this is a cascading clip.
                if len( self.cascade_completions ) < display.cascade_concurrency:
                    if self.cascade_filled:
                        clip.pts_offset = min( self.cascade_completions )
                    else:
                        clip.pts_offset = 0
                    self.cascade_completions.append( clip.pts_offset + clip.get_duration() )
                    if len( self.cascade_completions ) == display.cascade_concurrency:
                        self.cascade_filled = True
                else:
                    # Determine when we can begin the next cascade.
                    clip.pts_offset = min( self.cascade_completions )
                    # Remove clips that will end at that offset.
                    while self.cascade_completions.count( clip.pts_offset ):
                        self.cascade_completions.remove( clip.pts_offset )
                    self.cascade_completions.append( clip.pts_offset + clip.get_duration() )
                if max( self.cascade_completions ) > self.current_duration:
                    self.current_duration = max( self.cascade_completions )

            scale_clause = clip.get_scale_clause( self )

            cmd += ' [%s] trim=start=%s:end=%s:duration=%s,setpts=PTS-STARTPTS+%s/TB,%s [%s] ; ' % ( ilabel, clip.start, clip.end, clip.get_duration(), clip.pts_offset, scale_clause, olabel )
            
        # Overlay them onto one another
        if not Window.prior_overlay:
            Window.prior_overlay = 'base_%s' % ( self.label )

        # Build up a render for this window only.
        for idx, clip in enumerate( self.clips ):
            display = get_display( clip, self )

            if display.display_style != CASCADE:
                cmd += ' [%s] [%s] overlay=x=%d:y=%d:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, clip.label, self.x, self.y, Window.layer_idx )
            else:
                direction = display.cascade_direction

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

        return cmd

def get_display( clip, window ):
    if clip.display is not None:
        return clip.display
    elif window.display is not None:
        return window.display
    else:
        return Display()
        
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

    m1 = Watermark( '/wintmp/summary-test/logo.png',
                    x = "main_w-overlay_w-10",
                    y = "main_h-overlay_h-10",
                    fade_out_start = 3,
                    fade_out_duration = 1 )
    m2 = Watermark( '/wintmp/summary-test/logo128.png',
                    x = "trunc((main_w-overlay_w)/2)",
                    y = "trunc((main_h-overlay_h)/2)",
                    fade_in_start = -1,
                    fade_in_duration = 1 )
    
    w0 = Window( width=1280, height=1024, audio_filename='/wintmp/music/human405.m4a', duration = 10 )
    w1 = Window( display = d, height=1280, width=720, duration = w0.duration )
    w2 = Window( width=200, height=200, x=520, y=520, duration = w0.duration )
    w3 = Window( display=Display( display_style=CASCADE, cascade_direction=RIGHT ), bgcolor='White', width=1280, height=1024, duration = w0.duration )
    v1 = Video( 'test.mp4' )
    v2 = Video( 'flip.mp4' )    

    #w0.watermarks = [ m1, m2 ]

    c1 = Clip( v1, 1, 3 )    
    c2 = Clip( v1, 7, 8 )
    c3 = Clip( v2, 5, 6 )
    cx = Clip( v1, 4, 9 )
    c4 = Clip( v1, 4, 9, display=Display( display_style=CASCADE, cascade_direction = UP ) )
    c5 = Clip( v2, 0, 1, display=Display( display_style=CASCADE, cascade_direction = DOWN ) )
    c6 = Clip( v2, 1, 2, display=Display( display_style=CASCADE, cascade_direction = LEFT ) )
    c7 = Clip( v2, 2, 3, display=Display( display_style=CASCADE, cascade_direction = RIGHT ) )
    c8 = Clip( v2, 3, 5 )

    #w0.windows = [ w2 ]
    #w0.clips = [ cx ]
    #w2.clips = [ c2 ]
    #print w0.render()

    w1.windows = [ w2 ]
    w0.windows = [ w1 ]

    if 0:
        w2.clips = [ c3 ]
        w1.clips = [ c1, c2 ]
        w3.clips = [ c4, c5, c6, c7, c8 ]
    else:
        distribute_clips( [ c1, c2, c3, c8, cx ], [ w1, w2 ], w0.duration )

    result = w0.render()
    print result
    
        
        

    
