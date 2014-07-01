#!/usr/bin/env python

import commands
import datetime
from PIL import Image
import glob
from operator import itemgetter
import numpy
import os
import json
import pprint
import re
import requests
import shutil
from sqlalchemy import and_, not_, or_
from StringIO import StringIO
import sys

import vib.rekog.utils

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

import vib.utils.s3 as s3
#import vib.db.orm
#from vib.db.models import *

#root_dir = '/wintmp/youtube-test/beautifymeehtv/'
#root_dir = '/wintmp/youtube-test/brookers/'
root_dir = '/wintmp/youtube-test/gabeandjesss/'
indirs = glob.glob( '%s*' % ( root_dir ) )

bad_faces = []

for indir in indirs:
    if not os.path.isdir( indir ):
        continue

    good_faces = []
    
    bad_confidence = []
    bad_beauty = []
    bad_blur = []
    good_confidence = []
    good_beauty = []
    good_blur = []
    
    prior_movie = None;
    accepted_sequence = -99;

    #for movie in glob.glob( "%s/*mp4" % ( indir ) ):
    #    print "Working on:", movie
    #    if not os.path.isdir( "%s/images" % (indir ) ):
    #        os.makedirs( "%s/images" % ( indir ) )
    #    shortfile = os.path.basename( movie )
    #    cmd = 'ffmpeg -i %s -vf fps=fps=0.2 -f image2 %s/images/%s-%%05d.png' % ( movie, indir, shortfile )
    #    ( status, output ) = commands.getstatusoutput( cmd )
    #    print "Output was:", output

    #for filename in glob.glob( "%s/images/*.png" % ( indir ) ):
    #    if not os.path.isdir( "%s/album" % (indir ) ):
    #        os.makedirs( "%s/album" % ( indir ) )

    for filename in glob.glob( "%s/*.png" % ( indir ) ):
        if not os.path.isdir( "%s/album" % (indir ) ):
            os.makedirs( "%s/album" % ( indir ) )

        print "Working on %s" % ( filename )
        shortfile = os.path.basename( filename )
        sequence = int( re.search( u'images(\d+).png', shortfile ).groups()[0] )

        movie = os.path.split( indir )[-1]

        confidence = -1
        beauty = -1
        blur = -1

        if prior_movie != movie:
            accepted_sequence = -99
            prior_movie = movie
        
        if ( sequence - accepted_sequence ) < 9:
            continue
        
        ( status, output ) = commands.getstatusoutput( "/home/viblio/viblio/faces-working/faces/BlurDetector/blurDetector %s" % ( filename ) )
        print "Working on: %s" % ( filename )
        print status, output
        blur = float( output )

        if blur >=4:
            continue

        result = vib.rekog.utils.detect_for_file( filename )
        if result is not None and len( result['face_detection'] ) > 0:
            confidence = result['face_detection'][0]['confidence']
            beauty = result['face_detection'][0]['beauty']
        else:
            print "NO FACE FOUND!"

        if confidence > -1:
            bad_confidence.append( confidence )
        if beauty > -1:
            bad_beauty.append( beauty )
        bad_blur.append( blur )

        #if confidence > 0 and blur > 0:
        #    bad_faces.append( { "url" : shortfile,
        #                        "confidence" : confidence,
        #                        "beauty" : beauty,
        #                        "blur" : blur } )

        if ( ( confidence > 0.9 and blur < 4 ) or ( blur < 2 ) ):
            if sequence - accepted_sequence >= 9:
                shutil.copy( filename, '%s/album' % ( indir ) );
                accepted_sequence = sequence
                secs = 10 * max( 0, int( sequence ) - 3 )
                bad_faces.append( { "url" : shortfile,
                                    "confidence" : confidence,
                                    "beauty" : beauty,
                                    "blur" : blur,
                                    "movie_id" : movie,
                                    "secs" : secs } )

def get_col_lists( values, cols ):
    return [ values[i:i+cols] for i in range( 0, len( values ), cols ) ]

cols = 5
height = 128

    #bad_faces.sort( key=itemgetter( 'blur', 'confidence', 'beauty' ) )
    #bad_faces.reverse()

head_html = '''
<html>
<head>

<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>

<script>

"use strict";

function yt_album() {
	// Whenever a link is clicked, change the player iframe src to
	// the correct source.

	var yt_player;

	//first_video = $( "#thumbs a" ).attr( "href" );
	//first_video_id = first_video.match( /=(.*)&/ )[1]
	
	$( "#thumbs" ).on( 'click', "a", load_yt_player );

	function load_yt_player( event ) {
		event.preventDefault();
		console.log( "GOT HERE" );
		console.log( event );
		console.log( event.currentTarget.search );
		//var video_id = event.currentTarget.search.match( /=(.*)&/ )[1];
		//console.log( video_id );
		//var secs = parseInt( event.currentTarget.search.match( /&t=(\d+s)/ )[1] );
		//console.log( secs );
		//yt_player.loadVideoById( video_id, secs );
		//yt_player.playVideo()
		var url = event.currentTarget.search.slice(3).replace( "&t=", "?start=" );
		console.log( url );
		$( "#yt_player" ).attr( "src", "http://www.youtube.com/embed/" + url + "&autoplay=1" );
	}	

}

$( document ).ready( yt_album );

</script>

</head>
<body>

<div id="yt_container" >
  <iframe id="yt_player" width="640" height="360" src="" frameborder="1" allowfullscreen></iframe>
</div>

<div id="thumbs" style="overflow : auto; height:600;">
<table>
'''
back_html = '''
</table>
</div>
</body>
</html>
'''

# Display bad faces ordered by confidence, beauty:
b = open( "%s/collage.html" % ( root_dir ), 'w' )
body_html = ""
bad_cols = get_col_lists( bad_faces, cols )

for bad_col in bad_cols:
    body_html += "<tr>\n"
    for elem in bad_col:
        body_html += '<td><a href="https://youtube.com/watch?v=%s&t=%d" target="_blank" ><img src="%s/album/%s" height="%s" /></a></td>\n' % ( elem['movie_id'], elem['secs'], elem['movie_id'], elem['url'], height )
    body_html += "</tr>\n"
        
b.write( head_html )
b.write( body_html )
b.write( back_html )
b.close()
