#!/usr/bin/python

# 1. Create code to add data.
# 2. Create doco.
# 3. Create sample

# Add 15 videos for user.
# * At least one avi, mp4, mpeg, wmv
# Videos uploaded through tupsy

# Add 10 faces
#   * 1 recognized FB
#   * 1 recognized Viblio user
#   * 1 named user
#   * some unidentified users
# asset_type = image, time_stamp provided.

# meadia_asset_features
# One for each face, contact ID as appropriate.

# Media comments - One video has no comments, one has one, One has
# 100, the rest have 2.

# 1. Input us the user uuid.
# 2. Input is the tuspy parameters.
# 3. Download videos and faces from staging.
# 4. Upload through tuspy.
# 5. Insert additional faces associated with media for filename.
# 6. 


# TODO:
# 1. Fix "root" as the second position in logging.
# 2. Fix the "unable to resolve DEBUG" error.

import json
import uuid
import hmac
import os

import sys
sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'create_test_data' ).config()

from models import *


import boto
import requests
from boto.s3.key import Key

import logging
logging.basicConfig( filename = config['logfile'], level = config.loglevel )
log = logging.getLogger( "create_test_data" )

log.critical( "FOO create_test" )

from test_utils import upload_file_to_s3, download_file_from_s3

videos = [
    'test-01.mov',
    'test-02.mov',
    'test-03.mov',
    'test-04.MOV',
    'test-05.mov',
    'test-06.mov',
    'test-07.mov',
    'test-08.MTS',
    'test-09.mp4',
    'test-0a.mp4',
    'test-0b.mp4',
    ]

faces = [
    'face-01.jpg',
    'face-02.jpg',
    'face-03.jpg',
    'face-04.jpg',
    'face-05.jpg',
    'face-06.jpg',
    'face-07.jpg',
    'face-08.jpg',
    'face-09.jpg',
    'face-0a.jpg',
    ]

vid_dir = "/wintmp/test_files/"
face_dir = vid_dir + "faces/"

# File downloads from s3
# DEBUG get all videos
for video in videos[:1]:
    fname = video
    key = config.test_video_prefix + video
    download_file_from_s3( fname, key )

# DEBUG get all faces
for face in faces[:1]:
    fname = face
    key = config.test_face_prefix + face
    download_file_from_s3( fname, key )

# Upload video to through tupsy.

'''

for video in videos:
    fname = vid_dir + video
    key = config.test_video_prefix + video
    upload_file_to_s3( fname, key )

for face in faces:
    fname = face_dir + face
    key = config.test_face_prefix + face
    upload_file_to_s3( fname, key )

'''

'''

user = {
    'email' : 'foo@gmail.com'
    'id' : 1,
    'uuid' : 'deadbeef'
}

taggeduser = {}
shareduser = {}

# We have 15 videos.
videos = []

# We have 10 faces.
contacts = [
    { 'face' : 'filename.jpg', 'provider': 'local', 'provider_id':None, 
      'name' : 'name', 'email' : 'email', 'viblio_id' : None },
    ]





def create_test_user():
    pass

def upload_test_videos():
    pass

def upload_test_faces():
    add_face_to_media_assets()
    add_asset_feature_for_face()
    add_contact_for_face()
    pass


'''
