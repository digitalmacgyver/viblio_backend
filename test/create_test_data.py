#!/usr/bin/python

import logging
from optparse import OptionParser
import sys

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'create_test_data' ).config()

from test_utils import get_user_id_for_uuid, create_test_contacts, create_test_videos, upload_file_to_s3, download_file_from_s3

from test_data import faces, videos, contacts

logging.basicConfig( filename = config['logfile'], level = config.loglevel )
log = logging.getLogger( "create_test_data" )

verbose = False

# Connect to the database.
log.info( "Creating SQLAlchemy engine for: %s" % ( config.db_name ) )
engine = create_engine( 'mysql+mysqldb://'
                        +config.db_user+':'+config.db_pass
                        +config.db_conn
                        +config.db_name, echo=verbose )

user_uuid = None

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--user",
                  dest="user_uuid",
                  help="The existing user uuid of the user to add test data for." )

    (options, args) = parser.parse_args()

    if not options.user_uuid:
        parser.print_help()
        sys.exit(0)
    else:
        user_uuid = options.user_uuid

    log.info( "Getting user_id for uuid: %s" % ( user_uuid ) )
    user_id = get_user_id_for_uuid( engine, user_uuid )
    log.info( "User id is: %s" % ( user_id ) )

    create_test_contacts( engine, user_id, contacts )

    # DEBUG - today this doesn't put anything in S3, it just formulates
    # the rows in the database.
    create_test_videos( engine, user_id, videos, faces, contacts )




'''
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

'''

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

