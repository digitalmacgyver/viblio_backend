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

log = logging.getLogger( 'vib.utils.merge_accounts' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'merge_accounts: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

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

def merge_accounts( src_uuid, dest_uuid, verbose=False ):
    orm = None

    try:
        #import pdb
        #pdb.set_trace()

        orm = vib.db.orm.get_session()
    
        src_users = orm.query( Users ).filter( Users.uuid == src_uuid )
        if src_users.count() != 1:
            print "Found %s users with uuid %s, can't merge, returning." % ( src_users.count(), src_uuid )
            return False
        src_user = src_users[0]
        src_user_id = src_user.id

        dest_users = orm.query( Users ).filter( Users.uuid == dest_uuid )
        if dest_users.count() != 1:
            print "Found %s users with uuid %s, can't merge, returning." % ( dest_users.count(), dest_uuid )
            return False
        dest_user = dest_users[0]
        dest_user_id = dest_user.id

        # We don't copy:
        # Comments
        # User roles
        # Contact groups

        picture_uris = {}
        contact_ids = {}

        src_contacts = orm.query( Contacts ).filter( Contacts.user_id == src_user_id )
        dest_contacts = orm.query( Contacts ).filter( Contacts.user_id == dest_user_id )
        
        dest_contacts_by_email = {}

        for contact in dest_contacts:
            if not contact.is_group:
                if contact.contact_email is not None and contact.contact_email not in dest_contacts_by_email:
                    dest_contacts_by_email[contact.contact_email] = contact

        contact_old_new = {}
        # Add contacts ( not groups )
        for contact in src_contacts:
            if not contact.is_group:
                if contact.contact_email is not None and contact.contact_email in dest_contacts_by_email:
                    contact_ids[contact.id] = dest_contacts_by_email[contact.contact_email]
                    contact_old_new[contact.id] = dest_contacts_by_email[contact.contact_email].id

                    if verbose:
                        print "Skipping copy of contact for email %s, as the destination account already has one." % ( contact.contact_email )
                    continue

                old_contact_id = contact.id
                sqlalchemy.orm.session.make_transient( contact )
                contact.id = None
                contact.uuid = str( uuid.uuid4() )
                
                if contact.picture_uri in picture_uris:
                    picture_uris[contact.picture_uri].append( contact )
                else:
                    picture_uris[contact.picture_uri] = [ contact ]
                
                contact_ids[old_contact_id] = contact

                dest_user.contacts.append( contact )

                orm.commit()
                contact_old_new[old_contact_id] = contact.id

        src_media_files = orm.query( Media ).filter( Media.user_id == src_user_id )
        dest_media_files = orm.query( Media ).filter( Media.user_id == dest_user_id )
        media_old_new = {}
        media_uri_old_new = {}

        dest_media_by_hash = {}
        for m in dest_media_files:
            if not m.is_album:
                dest_media_by_hash[m.unique_hash] = m

        # Add media ( not albums )
        for m in src_media_files:
            if not m.is_album:
                if m.unique_hash is not None and m.unique_hash in dest_media_by_hash:
                    if verbose:
                        print "Skipping copy of media of unique hash %s, as the destination account already has one." % ( m.unique_hash )

                    media_old_new[m.id] = dest_media_by_hash[m.unique_hash].id
                    continue

                old_media_id = m.id
                src_assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == m.id )[:]

                sqlalchemy.orm.session.make_transient( m )
                m.id = None
                m_old_uuid = m.uuid
                m_new_uuid = str( uuid.uuid4() )
                m.uuid = m_new_uuid
                dest_user.media.append( m )
                
                orm.commit()
                media_old_new[old_media_id] = m.id

                for asset in src_assets:
                    features = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.media_asset_id == asset.id )[:]

                    sqlalchemy.orm.session.make_transient( asset )
                    asset.id = None
                    old_uuid = asset.uuid
                    old_uri = asset.uri
                    
                    if old_uri is None:
                        if verbose:
                            print "Warning, null old_uri for asset: %s" % ( asset.uuid )
                        continue

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
        for album in src_media_files:
            if album.is_album:
                album_media = orm.query( MediaAlbums ).filter( MediaAlbums.album_id == album.id ).all()
                assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == album.id )[:]

                sqlalchemy.orm.session.make_transient( album )
                album.id = None
                m_old_uuid = album.uuid
                m_new_uuid = str( uuid.uuid4() )
                album.uuid = m_new_uuid
                dest_user.media.append( album )
                orm.commit()

                for asset in assets:
                    features = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.media_asset_id == asset.id )[:]

                    sqlalchemy.orm.session.make_transient( asset )
                    asset.id = None
                    old_uuid = asset.uuid
                    old_uri = asset.uri

                    if old_uri is None:
                        if verbose:
                            print "Warning, null old_uri for asset: %s" % ( asset.uuid )
                        continue

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
                    if album_item.media_id in media_old_new:
                        new_media_album = MediaAlbums( album_id   = album.id, 
                                                       media_id = media_old_new[album_item.media_id] )
                        album.media_albums.append( new_media_album )
                    elif verbose:
                        print "Warning, no mapping for album item: %s, %s" % ( album_item.album_id, album_item.media_id )
                
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
    parser.add_option("-s", "--srcuser",
                      dest="src_uuid",
                      help="The user uuid of the user whose content should be copied from." )
    parser.add_option("-d", "--destuser",
                      dest="dest_uuid",
                      help="The user uuid of the user into whose account srcuser's content should be should be copied." )

    (options, args) = parser.parse_args()

    if not ( options.email or ( options.src_uuid and options.dest_uuid ) ):
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

    else:
        src_uuid = options.src_uuid
        dest_uuid = options.dest_uuid

        merge_accounts( src_uuid, dest_uuid, verbose=True )


