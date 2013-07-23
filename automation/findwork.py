#!/usr/bin/env python
#------------------------------------------------------------------------------
# Name:     findwork.py
# Purpose:  moves completed media files to S3 and creates corresponding database entries
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
import json
import time
import subprocess

while True:
    for filename in os.listdir(config.upload_dir):
        if filename.endswith('.json'):
            if filename.endswith('_metadata.json'):
                print 'ignore metadata file' + filename
            else:
                file_contents = open(config.upload_dir + filename)
                try:
                    parsed_contents = json.load (file_contents)
                    if parsed_contents.get('finalLength') == parsed_contents.get('offset'):
                        cmd = ["python", config.worker, filename]
                        child = subprocess.call( cmd, shell=False )
                        print cmd
                except:
                    print'bad json file: ' + filename
                    pass
    print 'looped'
    time.sleep(60)

