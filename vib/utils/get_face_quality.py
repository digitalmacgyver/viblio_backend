#!/usr/bin/env python

import commands
import datetime
from PIL import Image
from operator import itemgetter
import numpy
import os
import json
import pprint
import re
import requests
from sqlalchemy import and_, not_, or_
from StringIO import StringIO
import sys

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

def detect_faces( url ):
    '''Calls the ReKognition FaceDetect API and returns a Python data
    structure of the results.

    Return value is a hash with a 'face_detection' array (which can
    have multiple values).  Each face_detection element is a nested
    data structure with may fields.

    The outer structure is a hash, of particular interest is the:
    * confidence

    key.  If at most 1 face was expected, the face with highest
    confidence is probably the one you were searching for.
    '''
    try:
        data =  {
            "api_key"    : rekog_api_key, 
            "api_secret" : rekog_api_secret,
            "jobs"       : "face_beauty",
            "urls"       : url
            }
        r = requests.post( "http://rekognition.com/func/api/", data )
        return r.json()
    except Exception as e:
        print r.reason
        print r.text
        return None

orm = vib.db.orm.get_session()

from_when = datetime.datetime.utcnow() - datetime.timedelta( days=30 )

faces = orm.query( Media.filename, 
                   MediaAssets.uri,
                   MediaAssetFeatures.id,
                   MediaAssetFeatures.media_id,
                   MediaAssetFeatures.track_id,
                   MediaAssetFeatures.recognition_result,
                   MediaAssetFeatures.coordinates
                   ).filter( and_(
        Media.id == MediaAssets.media_id,
        Media.id == MediaAssetFeatures.media_id,
        MediaAssets.id == MediaAssetFeatures.media_asset_id,
        MediaAssetFeatures.feature_type == 'face',
        MediaAssetFeatures.recognition_result.in_( [ 'bad_face', 'not_face', 'machine_recognized', 'human_recognized', 'two_face' ] ),
        MediaAssetFeatures.created_date >= from_when ) )

bad_faces = []
good_faces = []

bad_confidence = []
bad_beauty = []
bad_blur = []
good_confidence = []
good_beauty = []
good_blur = []

prefix = "staging."

for f in faces:
    print "Working on %s" % ( f.id )
    confidence = -1
    beauty = -1
    blur = -1

    url = "https://%sviblio.com/s/ip/%s" % ( prefix, f.uri )
    filename = "/wintmp/blur-test/%s.jpg" % ( f.id )

    try:
        image_file = requests.get( url, stream=True )
        if image_file.status_code == 200:
            with open( filename, 'wb' ) as fo:
                for chunk in image_file.iter_content():
                    fo.write( chunk )

        ( status, output ) = commands.getstatusoutput( "/home/viblio/viblio/faces-working/faces/BlurDetector/blurDetector %s" % ( filename ) )
        print "Working on: %s %s" % ( url, filename )
        print status, output
        blur = float( output )
    except Exception as e:
        print "ERROR: %s" % ( e )

    result = detect_faces( url )
    if result is not None and len( result['face_detection'] ) > 0:
        confidence = result['face_detection'][0]['confidence']
        beauty = result['face_detection'][0]['beauty']
    else:
        print "NO FACE FOUND!"

    if f.recognition_result in [ 'bad_face', 'not_face' ]:
        bad_faces.append( { "url" : url,
                            "confidence" : confidence,
                            "beauty" : beauty,
                            "blur" : blur } )
        if confidence > -1:
            bad_confidence.append( confidence )
        if beauty > -1:
            bad_beauty.append( beauty )
        bad_blur.append( blur )
    elif f.recognition_result in [ 'machine_recognized', 'human_recognized', 'two_face' ]:
        good_faces.append( { "url" : url,
                            "confidence" : confidence,
                            "beauty" : beauty,
                             "blur" : blur } )
        if confidence > -1:
            good_confidence.append( confidence )
        if beauty > -1:
            good_beauty.append( beauty) 
        good_blur.append( beauty )
    else:
        print "ERROR - unexpected recognition result: %s" % ( f.recognition_result )
        sys.exit( 1 )

print "Good confidence: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( good_confidence ), numpy.median( good_confidence ), numpy.std( good_confidence ) )
print "Good beauty: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( good_beauty ), numpy.median( good_beauty ), numpy.std( good_beauty ) )
print "Good blur: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( good_blur ), numpy.median( good_blur ), numpy.std( good_blur ) )
print "Bad confidence: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( bad_confidence ), numpy.median( bad_confidence ), numpy.std( bad_confidence ) )
print "Bad beauty: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( bad_beauty ), numpy.median( bad_beauty ), numpy.std( bad_beauty ) )
print "Bad blur: \n\tavg: %0.02f\n\tmed: %0.02f\n\tsdv: %0.02f\n" % ( numpy.mean( bad_blur ), numpy.median( bad_blur ), numpy.std( bad_blur ) )

def get_col_lists( values, cols ):
    return [ values[i:i+cols] for i in range( 0, len( values ), cols ) ]

cols = 5
width = 128
height = 128

bad_faces.sort( key=itemgetter( 'confidence', 'beauty' ) )
bad_faces.reverse()
good_faces.sort( key=itemgetter( 'confidence', 'beauty' ) )
good_faces.reverse()

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
b = open( "bad_faces_blur.html", 'w' )
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

g = open( "good_faces_blur.html", 'w' )
body_html = ""
good_cols = get_col_lists( good_faces, cols )

for good_col in good_cols:
    body_html += "<tr>\n"
    for elem in good_col:
        body_html += '<td><img src="%s" width="%s" height="%s" /><ul><li>%0.02f</li><li>%0.02f</li><li>%0.02f</li></ul></td>\n' % ( elem['url'], width, height, elem['confidence'], elem['beauty'], elem['blur'] )
    body_html += "</tr>\n"
        
g.write( head_html )
g.write( body_html )
g.write( back_html )

