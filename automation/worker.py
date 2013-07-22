
#!/usr/bin/env python
#------------------------------------------------------------------------------
# Name:     work.py
# Purpose:  moves completed media files to S3 and creates corresponding database entries
#
# Author:   Bidyut Parruck   
#
# Created:  July 20th, 2013
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
import boto
import requests
import json
from boto.s3.key import Key

# Hardcoded parameters - needs to become variables later
uuid = 'BB374034-AAA0-11E2-9D76-00B897344F04'
mime_extension = '.mts'

# connect to Viblio S3 account and access the table of contents
s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
bucket = s3.get_bucket(config.bucket_name)
bucket_contents = Key(bucket)

# process one file at a time
for filename in os.listdir('/mnt/uploaded_files'):
    if filename.endswith('.json'):
        file_contents = open('/mnt/uploaded_files/' + filename)
        parsed_contents = json.load (file_contents)
# Process only completed files with 'state' = 'patched'
        if parsed_contents.get('finalLength') == parsed_contents.get('offset'):
# These should be handled by a forked process - one per completed file
# Eventually node server may directly call this script after file upload is completed
            media_filesize = parsed_contents.get('finalLength')
            s3_directory = filename.strip('.json')
            media_filename = filename.strip('.json') + mime_extension
            print s3_directory
# Create thumbnail and poster files
# command = 'ffmpeg -ss 10 -i /mnt/uploaded_files/' + s3_directory + ' -vframes 1 -f image2 - s 128x128 /mnt/uploaded_files/' + s3_directory + '_thumbnail.jpg'
            command = 'ffmpeg -v quiet -ss 10 -i /mnt/uploaded_files/' + s3_directory + ' -vframes 1 -f image2 -s 128x128 /mnt/uploaded_files/' + s3_directory + '_thumbnail.jpg'
            os.system (command)
            command = 'ffmpeg -v quiet -ss 10 -i /mnt/uploaded_files/' + s3_directory + ' -vframes 1 -f image2 -s 240x320 /mnt/uploaded_files/' + s3_directory + '_poster.jpg'
            os.system (command)
# Upload to S3
            s3_filename_with_path = s3_directory + '/' + media_filename
            local_filename_with_path = '/mnt/uploaded_files/' + s3_directory
            bucket_contents.key = s3_filename_with_path
            bucket_contents.set_contents_from_filename(local_filename_with_path)
            bucket_contents.key = s3_filename_with_path + '_thumbnail.jpg'
            bucket_contents.set_contents_from_filename(local_filename_with_path + '_thumbnail.jpg')
            bucket_contents.key = s3_filename_with_path + '_poster.jpg'
            bucket_contents.set_contents_from_filename(local_filename_with_path + '_poster.jpg')
            print 'uploaded ' + local_filename_with_path + ' to ' + s3_filename_with_path
# Update Viblio server
            params = {'uid': uuid, 'filename': media_filename, 'mimetype': 'video/' + mime_extension, 'size': media_filesize, 'location':'us', 'bucket_name': config.bucket_name,
              'uri': s3_directory + '/' + media_filename}
            r = requests.get(config.viblio_server_url, params=params)
            print r.text
# delete files, but check successful transfer before delete
#           os.remove('/mnt/uploaded_files/' + filename)
#           os.remove('/mnt/uploaded_files/' + 
