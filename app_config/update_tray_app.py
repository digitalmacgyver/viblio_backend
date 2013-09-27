#!/usr/bin/python

import logging
from optparse import OptionParser
import sys

import boto
from boto.s3.key import Key

from sqlalchemy import *

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( 'app_config' ).config()

from app_utils import show_configuration, upload_app_file

logging.basicConfig( filename = config['logfile'], level = config.loglevel )
log = logging.getLogger( config['app_name'] )
screen_output = logging.StreamHandler( sys.stdout )
screen_output.setLevel( logging.INFO )
log.addHandler( screen_output )


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
    parser.add_option( "-s", "--show-all",
                       dest="show_all",
                       action="store_true",
                       help="Show all app config in the database." )
    parser.add_option( "-a", "--app",
                       dest="app",  
                       help="The name of the app to update." )
    parser.add_option( "-c", "--current-version",
                       dest="version_string",
                       help="The new version string which is to be set to the current version.\nOnly numbers, letters, and .-_ are allowed in version names" )
    parser.add_option( "-f", "--file",
                       dest="input_file",
                       help="The path to the new tray app file to be uploaded to S3." )

    (options, args) = parser.parse_args()
    
    if not ( options.show_all or ( options.app and options.version_string and options.input_file and len( options.app ) and len( options.version_string ) and len( options.input_file ) ) ):
        parser.print_help()
        sys.exit(0)
    else:
        try:
            if options.show_all:
                log.info( 'Printing configuration information.' )
                show_configuration( engine )
            else:
                log.info( 'Uploading new version: %s of %s from file %s' % ( options.version_string, options.app, options.input_file ) )
                upload_app_file( engine, options.app, options.version_string, options.input_file )
                log.info( 'File upload complete.' )
                log.info( 'Current configuration data for all apps is:' )
                show_configuration( engine )
        except Exception as e:
            print 'Error occured: ' + str( e )
            log.error( 'Error occured: ' + str( e ) )
