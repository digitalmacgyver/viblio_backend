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

class _Display( object ):
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
        
    def get_duration( self ):
        return self.end - self.start

    def get_scale_clause( self, window ):
        display = None
        if self.display is not None:
            display = self.display
        elif window.display is not None:
            display = window.display
        else:
            display = _Display()

        if display.display_style == PAD:
            ( scale, ow, oh ) = self.get_output_dimensions( self.video.width, self.video.height, window.width, window.height, min )

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

            if scale != 1:
                scale_clause = "scale=width=%d:height=%d," % ( ow, oh )
                
            scale_clause += "crop=w=%d:h=%d" % ( window.width, window.height )

        elif display.display_style == PAN:
            # DEBUG, implement
            pass
        elif display.display_style == CASCADE:
            # DEBUG, implement
            pass
        else:
            raise Exception( "Error, unknown display style: %s" % ( display.display_style ) )

        return scale_clause
            
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
                  fade = "" ):

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
    video_inputs = {}
    layer_idx = 0
    prior_overlay = None

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
            self.display = _Display()

    def render( self ):
        '''Where the magic happens.'''

        #import pdb
        #pdb.set_trace()

        if len( self.windows ) == 0 and len( self.clips ) == 0:
            raise Exception( "Can't render with no clips and no child windows." )

        cmd = '%s -y -an ' % ( FFMPEG )
        for idx, video in enumerate( sorted( Video.videos.keys() ) ):
            cmd += " -i %s " % ( video )
            Window.video_inputs[video] = '%d:v' % ( idx )
            
        cmd += ' -filter_complex " color=%s:size=%sx%s [base_%s] ; ' % ( self.bgcolor, self.width, self.height, self.label )

        cmd += self.render_window()

        # DEBUG - actually handle the tail end here.
        # DEBUG - actually get to correct duration here.
        return cmd[:-8] + ' " -t 10 -strict -2 output.mp4'

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
            ilabel = Window.video_inputs[clip.video.filename]
            olabel = clip.label
            
            scale_clause = clip.get_scale_clause( self )

            cmd += ' [%s] trim=start=%s:end=%s:duration=%s,setpts=PTS-STARTPTS+%s/TB,%s [%s] ; ' % ( ilabel, clip.start, clip.end, clip.get_duration(), pts_offset, scale_clause, olabel )
            pts_offset += clip.get_duration()
    
        # Overlay them onto base
        if not Window.prior_overlay:
            Window.prior_overlay = 'base_%s' % ( self.label )
        for idx, clip in enumerate( self.clips ):
            cmd += ' [%s] [%s] overlay=x=%s:y=%s:eof_action=pass [o%s] ; ' % ( Window.prior_overlay, clip.label, self.x, self.y, Window.layer_idx )
            Window.prior_overlay = 'o%d' % ( Window.layer_idx )
            Window.layer_idx += 1

        return cmd
        
if __name__ == '__main__':
    
    # ??? Loop

    # Crop
    # Zoom/pan
    # Cascade
    # Total duration
    # Audio
    # Distribute clips
    # Watermark

    # This much is basically working.
    d = _Display( display_style = CROP )

    w1 = Window( display = d )
    w2 = Window( width=200, height=200, x=1080, y=520 )
    v1 = Video( 'test.mp4' )
    v2 = Video( 'flip.mp4' )

    c1 = Clip( v1, 1, 3 )
    c2 = Clip( v1, 7, 8 )
    c3 = Clip( v2, 5, 6 )

    w2.clips = [ c3 ]

    w1.clips = [ c1, c2 ]
    w1.windows = [ w2 ]

    print w1.render()

            
        
        

    
