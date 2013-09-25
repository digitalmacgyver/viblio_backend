#!/usr/bin/python

from optparse import OptionParser
import sys

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'test_data' ).config()

from test_utils import get_user_id_for_uuid, delete_all_data_for_user

import logging
logging.basicConfig( filename = config['logfile'], level = config.loglevel )
log = logging.getLogger( "delete_all_data_for_user" )


# Connect to the database.
engine = create_engine( 'mysql+mysqldb://'
                        +config.db_user+':'+config.db_pass
                        +config.db_conn
                        +config.db_name )

email = None

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The existing user uuid of the user to delete all data for." )

    (options, args) = parser.parse_args()

    if not options.user_uuid:
        parser.print_help()
        sys.exit(0)
    else:
        user_uuid = options.user_uuid

    log.info( "Getting user_id for uuid: %s" % ( user_uuid ) )
    user_id = get_user_id_for_uuid( engine, user_uuid )
    log.info( "User id is: %s" % ( user_id ) )

    delete_all_data_for_user( engine, user_id )
