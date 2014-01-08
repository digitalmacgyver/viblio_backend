#!/usr/bin/env python

# Simple utility script to manage our demonstration accounts, run via
# cron on prod-utils.

import commands
import json
import logging
from optparse import OptionParser
import os
import sys
import sqlalchemy
import uuid

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.manage_demo_accounts' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'manage_demo_accounts: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

baseline_account = 'demo@viblio.com'
demo_accounts = [ 'demo01@viblio.com', 'demo02@viblio.com', 'demo03@viblio.com' ]

#baseline_account = 'mjhayward+spock@gmail.com'
#demo_accounts = [ 'mjhayward+demo@gmail.com' ]

try:
    orm = vib.db.orm.get_session()

    baseline_user = orm.query( Users ).filter( Users.email == baseline_account )[:]

    if len( baseline_user ) != 1:
        message = 'Error, expected to find exactly one user for baseline account with email %s, found %s' % ( baseline_account, len( baseline_user ) )
        
        log.error( json.dumps( { 'message' : message } ) )
        raise Exception( message )

    baseline_uuid = baseline_user[0].uuid

    old_users = orm.query( Users ).filter( Users.email.in_( demo_accounts ) )

    log.info( json.dumps( { 'message' : 'Deleting old users.' } ) )
    for user in old_users:
        cmd = os.path.dirname( __file__ ) + '/delete_user.py -u %s -q' % ( user.uuid )
        log.info( json.dumps( { 'message' : 'About to run: %s' % ( cmd ) } ) )
        ( status, cmd_output ) = commands.getstatusoutput( cmd )
        log.debug( json.dumps( { 'message' : 'Output was: %s...' % ( cmd_output[:256] ) } ) )
        

    log.info( json.dumps( { 'message' : 'Cloning user %s' % ( baseline_account ) } ) )
    for account in demo_accounts:
        cmd = os.path.dirname( __file__ ) + '/clone_user.py -u %s -n %s' % ( baseline_uuid, account )
        log.info( json.dumps( { 'message' : 'About to run: %s' % ( cmd ) } ) )
        ( status, cmd_output ) = commands.getstatusoutput( cmd )
        log.debug( json.dumps( { 'message' : 'Output was: %s...' % ( cmd_output[:256] ) } ) )    
    
except Exception as e:
    log.error( json.dumps( { 'message' : 'Exception: %s' % ( e ) } ) )
