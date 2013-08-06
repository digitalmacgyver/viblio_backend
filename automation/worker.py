#!/usr/bin/env python
#------------------------------------------------------------------------------
# Name:     worker.py
# Purpose:  Copies completed media files to S3 and creates corresponding database entries
#
# Author:   Bidyut Parruck
#
# Created:  July 22th, 2013
# Licence:  Copyright Video Analytics, Inc.
#           All rights reserved
# To do:
# Fork a new python script for each patched file, data logging, error handling, checking before deleting files
# data logging - date, file size, file name + error logs (http://docs.python.org/2/howto/logging.html)
# error handling
#
#------------------------------------------------------------------------------
import config
import os
import sys
import logging
import boto
import requests
import json
from boto.s3.key import Key

filename = sys.argv[1]

logger = logging.getLogger('myapp')
hdlr = logging.FileHandler('/var/tmp/myapp.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.WARNING)


# Hardcoded parameters - needs to become variables later
uuid = '86FD9216-A8B9-11E2-9637-3B9C97344F04'
mime_extension = '.mp4'

file_contents = open(config.upload_dir + filename)
parsed_contents = json.load (file_contents)
media_filesize = parsed_contents.get('finalLength')
s3_directory = filename.strip('.json')
filename_only = filename.strip('.json')

# Create thumbnail and poster files
try:
    command = 'ffmpeg -v quiet -ss 1 -i ' +  config.upload_dir + s3_directory + ' -vframes 1 -f image2 -s 128x128 ' + config.upload_dir + s3_directory + '_thumbnail.jpg'
    print command
    os.system (command)
    command = 'ffmpeg -v quiet -ss 1 -i ' +  config.upload_dir + s3_directory + ' -vframes 1 -f image2 -s 240x320 ' + config.upload_dir + s3_directory + '_poster.jpg'
    print command
    os.system (command)
except:
    print 'thumbnail generation or poster generation failed'
    pass
# connect to Viblio S3 account and access the table of contents
try: 
    s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
    bucket = s3.get_bucket(config.bucket_name)
    bucket_contents = Key(bucket)

# Upload to S3
    local_filename_with_path = config.upload_dir + filename_only
    bucket_contents.key = s3_directory + '/' + filename_only + mime_extension
    bucket_contents.set_contents_from_filename(local_filename_with_path)

    bucket_contents.key = s3_directory + '/' + filename_only + '_thumbnail.jpg'
    bucket_contents.set_contents_from_filename(local_filename_with_path + '_thumbnail.jpg')

    bucket_contents.key = s3_directory + '/' + filename_only + '_poster.jpg'
    bucket_contents.set_contents_from_filename(local_filename_with_path + '_poster.jpg')

    bucket_contents.key = s3_directory + '/' + filename_only + '_metadata.json'
    bucket_contents.set_contents_from_filename(local_filename_with_path + '_metadata.json')    
    
    print 'uploaded ' + local_filename_with_path
    params = {'uid': uuid, 'filename': filename_only + mime_extension, 'mimetype': 'video/mp4', 'size': media_filesize, 'location':'us', 'bucket_name': config.bucket_name, 'uri': s3_directory + '/' + filename_only + mime_extension}
    r = requests.get(config.viblio_server_url, params=params)

# delete files, but check successful transfer before delete
    os.remove(local_filename_with_path + '.json')
    os.remove(local_filename_with_path)
    os.remove(local_filename_with_path + '_thumbnail.jpg')
    os.remove(local_filename_with_path + '_poster.jpg')
    os.remove(local_filename_with_path + '_metadata.json')
    
    
except:
    print 'S3 upload unsucessful'
    pass
# Update Viblio server
print r.text
