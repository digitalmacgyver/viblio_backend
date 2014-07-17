#!/usr/bin/env python

import commands
import glob
import os
import json
import re
import requests
import shutil
from sqlalchemy import and_, not_, or_
import sys

import vib.rekog.utils as rekog

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

APP_ID = '475476075863339'
APP_SECRET = 'bda5b255ce18a8bd0f9b57e3d3a4745b'
ENDPOINT = 'https://graph.facebook.com/'
ACCESS_TOKEN = 'CAAGwcWaZA3SsBAOlFegDcsOZBcPcauvzr5slTuaMixXKe9uZCS0mt258qc3h8atcinC8MOYBVZAry0xWxNf9BP9AfjIcy3En233csJx76OcpHLpuZBM5LXUKXHLO0dDZCIm0KHJp4oGabeM8ecDOt1rlSB0zyDUCqAwXVcCxGuv7ijPpfyWsZBB3cZBbIUdkFsIZD'

# Initially just download the images to local hard drive the better to
# run rekognition / blur detection on.

blur = os.path.dirname( __file__ ) + "/../cv/BlurDetector/blurDetector"
diff = os.path.dirname( __file__ ) + "/../cv/ImageDiff/imagediff"

orm = vib.db.orm.get_session()

# Also 887
images = orm.query( MediaAssets ).filter( and_( MediaAssets.asset_type == 'image', MediaAssets.user_id == 887 ) )

workdir = '/tmp/album/workdir/'

stats = {}

url_prefix = "staging."
url_prefix = ''

import pickle
if ( os.path.isfile( "%s/stats.txt" % ( workdir ) ) ):
    f = open( '%s/stats.txt' % ( workdir ), 'r' )
    stats = pickle.load( f )
    f.close()

for image in images:
    try:
        uri = image.uri
        timecode = image.timecode
        media_id = image.media_id
        asset_id = image.id
        filename = '%s/%s.png' % ( workdir, asset_id )

        face_score = image.face_score
        blur_score = image.blur_score

        print "Face score: %s, blur score: %s" % ( face_score, blur_score )
        stats[asset_id] = { 'url' : "https://%sviblio.com/s/ip/%s" % ( url_prefix, uri ),
                            'face_score' : face_score,
                            'blur_score' : blur_score,
                            'timecode' : timecode,
                            'media_id' : media_id,
                            'filename' : filename,
                            'asset_id' : asset_id }

    except Exception as e:
        print "ERROR: %s" % ( e )
    
f = open( '%s/stats.txt' % ( workdir ), 'w' )
pickle.dump( stats, f )
f.close()

# Create a new album.
url = ENDPOINT + "/me/albums?access_token=%s" % ( ACCESS_TOKEN )
data = { 
    'name' : 'Example Album 2',
}

r = requests.post( url, data )

print r.json()

album_id = r.json()['id']

print "Album id is: %s" % ( album_id )

r = requests.get( url )

print "Album is: %s" % r.json()

blur = []
faces = []

for image_key in sorted( stats.keys() ):
    image = stats[image_key]
    blur.append( image['blur_score'] )
    faces.append( image['face_score'] )

blur.sort()
faces.sort()

print blur
print faces

blur_threshold = 0
if len( blur ) > 4:
    blur_threshold = blur[ 3 * len( blur ) / 4 ]
print "Blur threshold is: ", blur_threshold

testdir = '/tmp/album/testdir'

blur_filter = True
face_filter = True
color_filter = False
time_filter = False

prior_image = None
current_image = None
prior_media = -1
prior_timecode = -99
gap_threshold = 15

#for i in [ 0.05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.1 ]:
for i in [ .2 ]:
    print "Diff threshold is:", i
    if not os.path.isdir( "%s/%s" % ( testdir, i ) ):
        os.makedirs( "%s/%s" % ( testdir, i ) )
                              
    for image_key in sorted( stats.keys(), key=lambda x: ( int( stats[x]['media_id'] ), float( stats[x]['timecode'] ) ) ):
        try:
            print "Working on i=%s: %s" % ( i, image_key )
            image = stats[image_key]
            
            #if not( image['blur_score'] < 0.36 or image['face_score'] >= 1 ):
            #    continue

            if blur_filter and image['blur_score'] > blur_threshold:
                continue
            if face_filter and image['face_score'] < 1:
                continue

            current_media = image['media_id']
            current_score = 1

            current_image = image['filename']
            if color_filter:
                if current_media == prior_media:
                    ( status, output ) = commands.getstatusoutput( "%s %s %s" % ( diff, prior_image, current_image ) )
                    current_score = float( output )
                    print "Score was: %s" % ( current_score )
                    if current_score <= i:
                        continue
                    prior_image = current_image
                else:
                    prior_image = current_image


            timecode = image['timecode'] 

            print "Score: %s, current_media: %s, prior_media: %s, timecode: %s, prior_timecode: %s" % ( current_score, current_media, prior_media, timecode, prior_timecode )

            if time_filter:
                if current_media == prior_media:
                    if timecode - prior_timecode < gap_threshold:
                        continue
                    else:
                        prior_timecode = timecode
                else:
                    prior_timecode = timecode

            prior_media = current_media

            print "UPLOADING IMAGE!"
            url = ENDPOINT + "%s/photos/?access_token=%s" % ( album_id, ACCESS_TOKEN )
            data = { 'url' : image['url'] }
            r = requests.post( url, data )
            print r.json()

        except Exception as e:
            print "ERROR: %s" % ( e ) 


