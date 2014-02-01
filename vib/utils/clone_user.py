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

format_string = 'clone_user: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

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
        # User roles
        # Contact groups
        # Media albums

        picture_uris = {}
        contact_ids = {}

        # Profiles
        profiles = orm.query( Profiles ).filter( Profiles.user_id == old_user_id )
        for profile in profiles:
            old_profile_id = profile.id

            sqlalchemy.orm.session.make_transient( profile )
            profile.id = None
            user.profiles.append( profile )

            profile_fields = orm.query( ProfileFields ).filter( ProfileFields.profiles_id == old_profile_id )
            for profile_field in profile_fields:
                sqlalchemy.orm.session.make_transient( profile_field )
                profile_field.id = None
                
                profile.profile_fields.append( profile_field )

        # Media shares
        media_shares = orm.query( MediaShares ).filter( MediaShares.user_id == old_user_id )
        for ms in media_shares:
            sqlalchemy.orm.session.make_transient( ms )
            ms.id = None
            ms.uuid = str( uuid.uuid4() )
            user.media_shares.append( ms )

        #import pdb
        #pdb.set_trace()

        contacts = orm.query( Contacts ).filter( Contacts.user_id == old_user_id )
        contact_old_new = {}
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

                orm.commit()
                contact_old_new[old_contact_id] = contact.id

        # Handle contact groups.
        for group in contacts:
            if group.is_group:
                group_contacts = orm.query( ContactGroups ).filter( ContactGroups.group_id == group.id ).all()

                sqlalchemy.orm.session.make_transient( group )
                group.id = None
                group.uuid = str( uuid.uuid4() )
                user.contacts.append( group )
                orm.commit()
                
                for group_member in group_contacts:
                    if group_member.contact_id is None:
                        new_contact_group = ContactGroups( group_id   = group.id, 
                                                           contact_viblio_id = group.contact_viblio_id )
                        group.contact_groups.append( new_contact_group )
                    elif group_member.contact_id in contact_old_new:
                        new_contact_group = ContactGroups( group_id   = group.id, 
                                                           contact_id = contact_old_new[group_member.contact_id], 
                                                           contact_viblio_id = group.contact_viblio_id )
                        group.contact_groups.append( new_contact_group )

        media_files = orm.query( Media ).filter( Media.user_id == old_user_id )
        media_old_new = {}
        media_uri_old_new = {}
        # Add media ( not albums )
        for m in media_files:
            if not m.is_album:
                old_media_id = m.id
                assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == m.id )[:]

                sqlalchemy.orm.session.make_transient( m )
                m.id = None
                m_old_uuid = m.uuid
                m_new_uuid = str( uuid.uuid4() )
                m.uuid = m_new_uuid
                user.media.append( m )
                
                orm.commit()
                media_old_new[old_media_id] = m.id

                for asset in assets:
                    features = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.media_asset_id == asset.id )[:]

                    sqlalchemy.orm.session.make_transient( asset )
                    asset.id = None
                    old_uuid = asset.uuid
                    old_uri = asset.uri
                    new_uri = old_uri.replace( m_old_uuid, m_new_uuid )

                    media_uri_old_new[old_uri] = new_uri

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

        # Handle media albums
        for album in media_files:
            if album.is_album:
                album_media = orm.query( MediaAlbums ).filter( MediaAlbums.album_id == album.id ).all()
                assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == m.id )[:]

                sqlalchemy.orm.session.make_transient( album )
                album.id = None
                m_old_uuid = album.uuid
                m_new_uuid = str( uuid.uuid4() )
                album.uuid = m_new_uuid
                user.media.append( album )
                orm.commit()

                for asset in assets:
                    features = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.media_asset_id == asset.id )[:]

                    sqlalchemy.orm.session.make_transient( asset )
                    asset.id = None
                    old_uuid = asset.uuid
                    old_uri = asset.uri

                    if old_uri in media_uri_old_new:
                        new_uri = media_uri_old_new[old_uri]
                    else:
                        old_substr = old_uri[:36]
                        new_uri = old_uri.replace( old_substr, m_new_uuid )

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

                    album.assets.append( asset )

                    for feature in features:
                        sqlalchemy.orm.session.make_transient( feature )
                        feature.id = None
                        asset.media_asset_features.append( feature )
                        if feature.contact_id is not None and feature.contact_id in contact_ids:
                            contact_ids[feature.contact_id].media_asset_features.append( feature )

                for album_item in album_media:
                    if album_item.media_id is None:
                        new_media_album = MediaAlbums( album_id   = album.id )
                        album.media_albums.append( new_media_album )
                    elif album_item.media_id in media_old_new:
                        new_media_album = MediaAlbums( album_id   = album.id, 
                                                       media_id = media_old_new[album_item.media_id] )
                        album.media_albums.append( new_media_album )
                
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


