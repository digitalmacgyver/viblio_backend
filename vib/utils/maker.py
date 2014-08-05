#!/usr/bin/env python

import commands
import glob
import random
import re

videos = []

overlay_string = ''
prior = '[base]'

total_duration = 0

ffmpeg = 'ffmpeg -y '
filter_complex = ' color=Black:size=640x360 [base] ; '

for idx, video_file in enumerate( glob.glob( 'clips/*.mp4' ) ):
    ( status, output ) = commands.getstatusoutput( 'ffmpeg -i %s' % ( video_file ) )
    hms = re.search( r'Duration: (\d\d):(\d\d):([\d\.]+)', output ).groups()
    if len( hms ) == 3:
        duration = 60*60*int( hms[0] ) + 60*int( hms[1] ) + float( hms[2] )
        
    clip_duration = duration
    slowmo = ''
    if duration < 3:
        slowmo += ",setpts=%s*PTS" % ( 3 / duration ) 
        clip_duration = 3
    
    if total_duration < 2*idx+clip_duration:
        total_duration = 2*idx+clip_duration

    scale = random.uniform( 1.0/2, 1.0/6 )
    width = 2*int( 640*scale/2 )
    height = 2*int( 360*scale/2 )

    video_string = "[%d:v] scale=%d:%d%s [v%d]" % ( idx, width, height, slowmo, idx )
    videos.append( {
            'video_file' : video_file,
            'video_string' : video_string,
            'duration' : clip_duration,
            'width' : width,
            'height' : height
            } )

    ffmpeg += ' -itsoffset %d -i %s ' % ( 2*idx, video_file )
    filter_complex += ' %s ; ' % ( video_string )
    print video_string

    if idx > 0:
        overlay_string += " [o%d]; " % ( idx - 1 )
    x = random.randint( 0, 640-width )
    y = "'if( gte(t,%d), -h+(t-%d)*%f, NAN)'" % ( idx*2, idx*2, float( 360+height ) / clip_duration )
    overlay_string += "%s[v%d] overlay=x=%s:y=%s " % ( prior, idx, x, y )
    prior = "[o%d]" % ( idx )

cmd = '%s -filter_complex " %s %s " -t %f test.mp4' % ( ffmpeg, filter_complex, overlay_string, total_duration )

print "Running:", cmd

( status, output ) = commands.getstatusoutput( cmd )

print "output was: ", output

#print overlay_string



    #string = "[v%d][v%d] [v%d]
