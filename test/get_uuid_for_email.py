#!/usr/bin/python

from optparse import OptionParser
import sys

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'create_test_data' ).config()

from test_utils import get_user_id_for_uuid, create_test_contacts, create_test_videos, upload_file_to_s3, download_file_from_s3, get_uuid_for_email

# Connect to the database.
engine = create_engine( 'mysql+mysqldb://'
                        +config.db_user+':'+config.db_pass
                        +config.db_conn
                        +config.db_name )

email = None

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-e", "--email",
                  dest="email",
                  help="The email address of the user you want the uuid for." )

    (options, args) = parser.parse_args()

    if not options.email:
        parser.print_help()
        sys.exit(0)
    else:
        email = options.email

    found = False
    for uuid in get_uuid_for_email( engine, email ):
        print "Found uuid:", uuid[0], "for email:", email
        found = True

    if not found:
        print "No user found for email:", email

