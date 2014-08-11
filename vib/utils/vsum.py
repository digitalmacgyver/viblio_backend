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

def distribute_clips( clips=[], windows=[] ):
    pass


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
            # DEBUG
            # ffmpeg -i and re to get the relevant data for the video.
            # Assign instance variables.
            self.duration = 10.01
            self.width = 720
            self.height = 576
            #DEBUG
            Video.videos[filename] = { 'width'    : self.width,
                                       'height'   : self.height,
                                       'duration' : self.duration }
        
class Clip( object ):
    idx = 0

    def __init__( self,
                  video,
                  start               = 0,
                  end                 = None,
                  display             = None ):
        
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


                  
class Watermark( object ):
    def __init__( self, 
                  filename,
                  scale = "",
                  x = 0,
                  y = 0,
                  fade = "",
                  loop = "" ):

        if not os.path.exists( filename ):
            raise Exception( "No watermark media found at: %s" % ( filename ) )
        else:
            self.filename = filename

        self.scale = scale
        self.x = x
        self.y = y
        self.fade = fade

class Window( object ):
    idx = 0
    z = 0
    media_inputs = {}
    layer_idx = 0
    prior_overlay = None
    total_duration = 0

    def __init__( self,
                  windows = None,
                  clips = None,
                  bgcolor = 'Black',
                  width = 1280,
                  height = 720,
                  x = 0,
                  y = 0,
                  loop = True,
                  duration = None,
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
        self.loop     = loop
        self.duration = duration

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

        if display is not None:
            self.display = display
        else:
            self.display = Display()

        self.cascade_completions = []

    def render( self ):
        '''Where the magic happens.'''

        #import pdb
        #pdb.set_trace()

        if len( self.windows ) == 0 and len( self.clips ) == 0:
            raise Exception( "Can't render with no clips and no child windows." )

        cmd = '%s -y -r 30000/1001 -c:a libfdk_acc -an ' % ( FFMPEG )
        video_count = 1
        for idx, video in enumerate( sorted( Video.videos.keys() ) ):
            cmd += " -i %s " % ( video )
            Window.media_inputs[video] = '%d:v' % ( idx )
            video_count = idx

        for idx, watermark in enumerate( self.watermarks ):
            cmd += " -i %s %s " % ( watermark.filename, watermark.loop )
            Window.media_inputs[watermark.filename] = '%d:v' % ( video_count + idx )

        # DEBUG
        #cmd += " -i %s " % ( self.audio_filename )
        #Window.media_inputs[self.audio_filename] = '%d:a' % ( video_count + len( self.watermarks ) )

            
        cmd += ' -filter_complex " color=%s:size=%sx%s [base_%s] ; ' % ( self.bgcolor, self.width, self.height, self.label )

        cmd += self.render_window()

        cmd += self.add_watermarks()

        # DEBUG - actually handle the tail end here.
        # DEBUG - actually get to correct duration here.
        return cmd[:-8] + ' " -t %d -strict -2 output.mp4' % ( Window.total_duration )

    def add_watermarks( self ):
        cmd = ""
        # DEBUG - actually do something here.
        for watermark in self.watermarks:
            cmd += "[%s] %s"

        return cmd

    def render_window( self ):
        # We render clips first, then windows on top of them.
        cmd = self.add_clips( self.clips )

        # Then we recursively descend into our child windows.
        for window in sorted( self.windows, key=lambda x: x.z_index ):
            cmd += window.render_window()
            
        #import pdb
        #pdb.set_trace()
        return cmd

    def add_clips( self, clips ):
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
                if pts_offset > Window.total_duration:
                    Window.total_duration = pts_offset
            else:
                # It's complicated if this is a cascading clip.
                if len( self.cascade_completions ) < display.cascade_concurrency:
                    if len( self.cascade_completions ):
                        clip.pts_offset = min( self.cascade_completions )
                    else:
                        clip.pts_offset = 0
                    self.cascade_completions.append( clip.pts_offset + clip.get_duration() )
                else:
                    # Determine when we can begin the next cascade.
                    clip.pts_offset = min( self.cascade_completions )
                    # Remove clips that will end at that offset.
                    while self.cascade_completions.count( clip.pts_offset ):
                        self.cascade_completions.remove( clip.pts_offset )
                    self.cascade_completions.append( clip.pts_offset + clip.get_duration() )
                if max( self.cascade_completions ) > Window.total_duration:
                    Window.total_duration = max( self.cascade_completions )

            scale_clause = clip.get_scale_clause( self )

            cmd += ' [%s] trim=start=%s:end=%s:duration=%s,setpts=PTS-STARTPTS+%s/TB,%s [%s] ; ' % ( ilabel, clip.start, clip.end, clip.get_duration(), clip.pts_offset, scale_clause, olabel )
            
            # Overlay them onto one another
            if not Window.prior_overlay:
                Window.prior_overlay = 'base_%s' % ( self.label )
            for idx, clip in enumerate( self.clips ):
                if display.display_style != CASCADE:
                    cmd += ' [%s] [%s] overlay=x=%s:y=%s:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, clip.label, self.x, self.y, Window.layer_idx )
                else:
                    # DEBUG - handle different directions.

                    # DEBUG - I HAVE A BUG HERE, BUT ALSO THERE IS A BUG WHEN A SINGLE CLIP IS USED IN DIFFERENT PLACES, WITH IT ONLY HAVING 1 WIDTH, PTS OFFSET, ETC.
                    x = self.x + random.randint( 0, self.width - clip.width )
                    y = "'%d + if( gte(t,%d), -h(t-%d)*%f, NAN)'" % ( self.y, clip.pts_offset, clip.pts_offset, float( self.height+clip.height ) / clip.get_duration() )
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
    
    # ??? Loop

    # ??? Cascade

    # Audio
    # Distribute clips
    # Watermark

    # This much is basically working.
    d = Display( display_style = PAN )

    w1 = Window( display = d, height=1280, width=720 )
    w2 = Window( width=200, height=200, x=520, y=520 )
    w3 = Window( display=Display( display_style=CASCADE ), bgcolor='White', width=1280, height=1024 )
    v1 = Video( 'test.mp4' )
    v2 = Video( 'flip.mp4' )

    c1 = Clip( v1, 1, 3 )
    c2 = Clip( v1, 7, 8 )
    c3 = Clip( v2, 5, 6 )



    w2.clips = [ c3 ]

    w1.clips = [ c1, c2 ]
    w1.windows = [ w2 ]

    w3.windows = [ w1 ]

    w3.clips = [ c2, c3, c1 ]
    print w3.render()

            
        
        

    
