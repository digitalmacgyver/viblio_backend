#!/usr/bin/env python

import json
import logging
from logging import handlers
from optparse import OptionParser
import os
import shutil
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )
format_string = 'cleanup_temp_files: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def cleanup_dir( directory, days_old ):
    log.info( json.dumps( { "message" : "Cleaning up temp directories under: %s" % ( directory ) } ) )            

    if not os.path.isdir( directory ):
        log.info( json.dumps( { "message" : "Directory %s doesn't exist, skipping." % ( directory ) } ) )            
        return

    for r, d, f in os.walk( directory ):
        for temp_dir in d:
            if temp_dir != 'errors':
                full_temp_dir = os.path.join( r, temp_dir )
                mtime = os.path.getmtime( full_temp_dir )
                age = float( time.time() - mtime ) /24/60/60
                if age > days_old:
                    log.info( json.dumps( { "message" : "Recursively deleting directory %s (%d days old)." % ( full_temp_dir, age ) } ) )            
                    if full_temp_dir[:4] != '/mnt':
                        log.error( json.dumps( { 'message' : 'Error, refusing to delete directories not under /mnt.' } ) )
                        raise Exception( "Directories must begin with /mnt for safety." )
                    else:
                        try:
                            shutil.rmtree( full_temp_dir )
                        except Exception as e:
                            log.error( json.dumps( { 'message' : 'Error, failed to delete directory %s, error was %s' % ( full_temp_dir, e ) } ) )


    log.info( json.dumps( { "message" : "Cleaning up temp files under: %s" % ( directory ) } ) )            
    for temp_file in os.listdir( directory ):
        full_temp_file = os.path.join( directory, temp_file )
        if not os.path.isfile( full_temp_file ):
            continue
        else:
            mtime = os.path.getmtime( full_temp_file )
            age = float( time.time() - mtime ) /24/60/60
            if age > days_old:
                log.info( json.dumps( { "message" : "Deleting file %s (%d days old)." % ( full_temp_file, age ) } ) )            
                if full_temp_file[:4] != '/mnt':
                    log.error( json.dumps( { 'message' : 'Error, refusing to delete files not under /mnt.' } ) )
                    raise Exception( "Files must begin with /mnt for safety." )
                else:
                    try:
                        os.remove( full_temp_file )
                    except Exception as e:
                        log.error( json.dumps( { 'message' : 'Error, failed to delete file %s, error was %s' % ( full_temp_file, e ) } ) )

    return


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option( '-d', '--days', dest="days_old", 
                       help="The age of temporary files in days older than which we should delete (floating point).  Default is 2" )
    
    ( options, args ) = parser.parse_args()

    days_old = 2.0
    if options.days_old:
        days_old = float( options.days_old )

    log.info( json.dumps( { "message" : "Deleting temp directories last modified more than %s days ago." % ( days_old ) } ) )

    directories = [  config.transcode_dir, 
                     config.transcode_dir+'/errors', 
                     config.faces_dir, 
                     config.activity_dir ]

    for temp_dir in directories:
        cleanup_dir( temp_dir, days_old )
