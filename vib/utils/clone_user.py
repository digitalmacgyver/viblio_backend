#!/usr/bin/env python

import logging
from optparse import OptionParser
import sys
import sqlalchemy
import uuid

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.clone_user' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'rescue_orphan_faces: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

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

def clone_user( user_uuid, new_email, verbose=False ):
    orm = None

    try:
        #import pdb
        #pdb.set_trace()

        orm = vib.db.orm.get_session()
    
        users = orm.query( Users ).filter( Users.uuid == user_uuid )

        if users.count() != 1:
            print "Found %s users with uuid %s, can't clone, returning." % ( users.count(), user_uuid )
            return 0

        user = users[0]
        old_user_id = user.id

        sqlalchemy.orm.session.make_transient( user )
        user.id = None
        user.uuid = str( uuid.uuid4() )
        user.email = new_email

        # Add new new user.
        orm.add( user )

        # Add the new user to the beta whitelist.
        whitelist = EmailUsers( 
            email = new_email, 
            status = 'whitelist'
            )
        orm.add( whitelist )

        # We don't copy:
        # Comments
        # Profile settings
        # User roles
        # Contact groups
        # Media albums

        # We don't copy comments
        # We don't copy shares

        picture_uris = {}
        contact_ids = {}

        # Media shares
        media_shares = orm.query( MediaShares ).filter( MediaShares.user_id == old_user_id )
        for ms in media_shares:
            sqlalchemy.orm.session.make_transient( ms )
            ms.id = None
            ms.uuid = str( uuid.uuid4() )
            user.media_shares.append( ms )

        contacts = orm.query( Contacts ).filter( Contacts.user_id == old_user_id )
        # Add contacts ( not groups )
        for contact in contacts:
            if not contact.is_group:
                old_contact_id = contact.id
                sqlalchemy.orm.session.make_transient( contact )
                contact.id = None
                contact.uuid = str( uuid.uuid4() )
                
                if contact.picture_uri in picture_uris:
                    picture_uris[contact.picture_uri].append( contact )
                else:
                    picture_uris[contact.picture_uri] = [ contact ]
                
                contact_ids[old_contact_id] = contact

                user.contacts.append( contact )

        media_files = orm.query( Media ).filter( Media.user_id == old_user_id )
        # Add media ( not albums )
        for m in media_files:
            if not m.is_album:
                assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == m.id )[:]

                sqlalchemy.orm.session.make_transient( m )
                m.id = None
                m_old_uuid = m.uuid
                m_new_uuid = str( uuid.uuid4() )
                m.uuid = m_new_uuid
                user.media.append( m )
                
                for asset in assets:
                    features = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.media_asset_id == asset.id )[:]

                    sqlalchemy.orm.session.make_transient( asset )
                    asset.id = None
                    old_uuid = asset.uuid
                    old_uri = asset.uri
                    new_uri = old_uri.replace( m_old_uuid, m_new_uuid )

                    if old_uri in picture_uris:
                        for contact in picture_uris[old_uri]:
                            contact.picture_uri = new_uri
                        
                    new_uuid = str( uuid.uuid4() )
                    asset.uuid = new_uuid
                    asset.uri = new_uri
                    try:
                        s3.copy_s3_file( config.bucket_name, old_uri, config.bucket_name, new_uri )
                    except Exception as e:
                        print "Error copying S3 file: %s" % ( e )

                    m.assets.append( asset )

                    for feature in features:
                        sqlalchemy.orm.session.make_transient( feature )
                        feature.id = None
                        asset.media_asset_features.append( feature )
                        if feature.contact_id is not None and feature.contact_id in contact_ids:
                            contact_ids[feature.contact_id].media_asset_features.append( feature )
                
        orm.commit()

        if verbose:
            print "Done"

    except Exception as e:
        print "Error: %s, rolling back (note: s3 operations can not be rolled back)" % ( e )

        if orm:
            orm.rollback()

if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-e user@email.com]|[-u user-uuid] [-n user2@email.com]"
    parser = OptionParser( usage = usage )
    parser.add_option("-e", "--email",
                  dest="email",
                  help="Print the uuid(s) associated with the email and exit." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The user uuid of the user to clone." )
    parser.add_option("-n", "--new-email",
                      dest="new_email",
                      help="The email the newly created clone should have." )

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

    elif options.user_uuid and options.new_email:
        user_uuid = options.user_uuid
        new_email = options.new_email

        clone_user( user_uuid, new_email, verbose=True )
    else:
        print "Must provide either -e or both -u and -n arguments."


