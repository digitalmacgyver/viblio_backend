#!/usr/bin/env python

import logging
from optparse import OptionParser
from sqlalchemy import and_
import sys

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.delete_user' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'delete_user: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def get_uuid_for_email( email ):
    orm = vib.db.orm.get_session()

    uuids = []

    for user in orm.query( Users ).filter( Users.email == email ):
        uuids.append( user.uuid )

    return uuids

def get_input( question, default="no" ):
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write( question + prompt )
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")

def delete_all_data_for_user( user_uuid, delete_user=True, verbose=False ):
    orm = None

    try:
        orm = vib.db.orm.get_session()
    
        user = orm.query( Users ).filter( Users.uuid == user_uuid )

        if user.count() != 1:
            print "Found %s users with uuid %s, returning without deleting anything." % ( user.count(), user_uuid )
            return 0

        user_id = user[0].id

        media = orm.query( Media ).filter( Media.user_id == user[0].id )
        assets = orm.query( MediaAssets ).filter( MediaAssets.user_id == user_id )
        contacts = orm.query( Contacts ).filter( Contacts.user_id == user_id )
    
        if verbose:
            print "About to delete all data for user %s with uuid %s" % ( user[0].email, user[0].uuid )
            print "User has:"
            print "\t%s media items" % media.count()
            print "\t%s contacts" % contacts.count()
            proceed = get_input( "Proceed?", "no" )
            if not proceed:
                print "Canceling, no data will be deleted."
                return 0

        # Note, we only get here if !verbose, or verbose and proceed.
        delete_keys = []
        for asset in assets:
        
            asset_type = asset.asset_type
            asset_id = asset.id
            key = asset.uri

            if verbose:
                print "Deleting %s %s from s3 %s/%s" % ( asset_type, asset_id, config.bucket_name, key )
                
            delete_keys.append( key )
            
            if len( delete_keys ) == 1000:
                s3.delete_s3_files( config.bucket_name, delete_keys )
                delete_keys = []

        s3.delete_s3_files( config.bucket_name, delete_keys )

        if verbose:
            print "Deleting all contacts for user %s" % ( user_uuid )
            
        orm.query( Contacts ).filter( and_( Contacts.user_id == user_id, Contacts.is_group == True ) ).delete()
        orm.query( Contacts ).filter( Contacts.user_id == user_id ).delete()

        if delete_user:
            if verbose:
                print "Deleting user and all comments, shares, media, media_assets, media_asset_features, and the user %s itself" % ( user_uuid )            
            orm.query( Media ).filter( and_( Media.user_id == user_id, Media.is_album == True ) ).delete()
            orm.query( Users ).filter( Users.id == user_id ).delete()
        else:
            # Delete everything about this user, but leave the user in
            # tact.
            if verbose:
                print "Deleting all comments, shares, media, media_assets, media_asset_features, and the user %s itself" % ( user_uuid )            
            orm.query( Media ).filter( and_( Media.user_id == user_id, Media.is_album == True ) ).delete()
            orm.query( Media ).filter( Media.user_id == user_id ).delete()
        
        orm.commit()

        try:
            if verbose:
                print "Deleting all face recognition data for user_id %s" % ( user_id )
                rec.delete_user( user_id )
        except Exception as e:
            print "Error deleting face recognition data: %s" % ( e )

        orm.commit()

        if verbose:
            print "Done"

    except Exception as e:
        print "Error: %s, rolling back (note: s3 deletions can not be rolled back)" % ( e )

        if orm:
            orm.rollback()

if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-e user@email.com]|[-u user-uuid] [-d] [-q]"
    parser = OptionParser( usage = usage )
    parser.add_option("-e", "--email",
                  dest="email",
                  help="Print the uuid(s) associated with the email and exit." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The user uuid of the user to delete all data for." )
    parser.add_option( '-d', '--data-only', action="store_true", default=False,
                       dest='data_only',
                       help='Only delete the user data, but leave the user itself in tact.' )
    parser.add_option( '-q', '--quiet', action="store_true", default=False,
                       dest='quiet',
                       help='Run in quiet mode with limited output and no interactive prompts.' )


    (options, args) = parser.parse_args()

    if not ( options.email or options.user_uuid ):
        parser.print_help()
        sys.exit(0)
    elif options.email:
        email = options.email

        found = False

        for uuid in get_uuid_for_email( email ):
            print "Found uuid:", uuid, "for email:", email
            found = True

        if not found:
            print "No user found for email:", email

    elif options.user_uuid:
        user_uuid = options.user_uuid
        verbose = not options.quiet

        if options.data_only:
            delete_all_data_for_user( user_uuid, delete_user=False, verbose=verbose )
        else:
            delete_all_data_for_user( user_uuid, delete_user=True, verbose=verbose )           


