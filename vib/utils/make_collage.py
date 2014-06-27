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
import vib.db.orm
from vib.db.models import *

bad_faces = []
good_faces = []

bad_confidence = []
bad_beauty = []
bad_blur = []
good_confidence = []
good_beauty = []
good_blur = []

prior_movie = None;
accepted_sequence = -99;

for filename in glob.glob( "/wintmp/wedding-album/images/*png" ):
    print "Working on %s" % ( filename )
    shortfile = os.path.basename( filename )
    movie = re.match( u'(\d+)\.mp4-\d+.png', shortfile ).groups()[0]
    sequence = int( re.search( u'\d+\.mp4-(\d+).png', shortfile ).groups()[0] )
    confidence = -1
    beauty = -1
    blur = -1

    if prior_movie != movie:
        accepted_sequence = -99
        prior_movie = movie

    if ( sequence - accepted_sequence ) < 18:
        continue
        
    ( status, output ) = commands.getstatusoutput( "/home/viblio/viblio/faces-working/faces/BlurDetector/blurDetector %s" % ( filename ) )
    print "Working on: %s" % ( filename )
    print status, output
    blur = float( output )

    if blur >=2 :
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

    if confidence > 0 and blur > 0:
        bad_faces.append( { "url" : shortfile,
                            "confidence" : confidence,
                            "beauty" : beauty,
                            "blur" : blur } )

    if ( ( confidence > 0.9 and blur < 2 ) or ( blur < 1 ) ):
        if sequence - accepted_sequence >= 18:
            shutil.copy( filename, '/wintmp/wedding-album/selected' );
            accepted_sequence = sequence


def get_col_lists( values, cols ):
    return [ values[i:i+cols] for i in range( 0, len( values ), cols ) ]

cols = 5
width = 128
height = 128

bad_faces.sort( key=itemgetter( 'blur', 'confidence', 'beauty' ) )
bad_faces.reverse()

head_html = '''
<html>
<head></head>
<body>
<table>
'''
back_html = '''
</table>
</body>
</html>
'''

# Display bad faces ordered by confidence, beauty:
b = open( "collage.html", 'w' )
body_html = ""
bad_cols = get_col_lists( bad_faces, cols )

for bad_col in bad_cols:
    body_html += "<tr>\n"
    for elem in bad_col:
        body_html += '<td><img src="%s" width="%s" height="%s" /><ul><li>%0.02f</li><li>%0.02f</li><li>%0.02f</li></ul></td>\n' % ( elem['url'], width, height, elem['confidence'], elem['beauty'], elem['blur'] )
    body_html += "</tr>\n"
        
b.write( head_html )
b.write( body_html )
b.write( back_html )

