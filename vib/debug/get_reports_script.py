#!/usr/bin/env python

from __future__ import print_function
import logging
import os,json
from Loggly import Loggly

logging.basicConfig(level=logging.INFO, format="%(message)s")
print = logging.info
##############################################################

# Search parameters
n_hours = 24*3
user = 'mehran'
password = '87kE8V56'
quiet = False # Log info
if quiet:
	logging.basicConfig(level=logging.ERROR)

# Report
log = Loggly(user,password)
print('Fetching error logs')
errors = log.get_errors(n_hours)
folder_name = './reports'
if not os.path.exists(folder_name):
	os.makedirs(folder_name)
error_media_uuids = set(map(lambda x: x['event']['json']['activity_log']['media_uuid'], errors))

print(errors)

import sys
sys.exit(0)

print(str(len(error_media_uuids)) + ' error logs found.')
for media_uuid in error_media_uuids:
	print('Fetching logs of media_uuid:`'+media_uuid+'`.')
	messages = log.get_messages(media_uuid, n_hours)
	print('Writing logs to file.')
	report_file = open(os.path.join(folder_name,media_uuid+'.txt'), 'w')
	report_file.write(json.dumps(messages, indent=4))
	report_file.close()
