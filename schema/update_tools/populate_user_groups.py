#!/usr/bin/env python

import datetime
import logging
from logging import handlers
import pickle
from sqlalchemy import and_, distinct, func
import time
import uuid

import vib.cv.FaceRecognition.UIInterface
import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib' )
log.setLevel( logging.DEBUG )

format_string = 'populate_user_groups: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )
log.addHandler( consolelog )

orm = vib.db.orm.get_session()

f = open( "contacts.txt" )
contacts = pickle.load( f )
f.close()

# We have the following tasks:

# FOR CONTACTS WITH IS_GROUP != 1

# 1. For each user who has contacts, create a new group of type
# contact.
# 2. For each contact, establish a user for that contact - either a
# new user with user_type contact, or an existing user based on email.
# 3. For each contact associated with a user X, associate the user
# from step 2 with thr group from step 1.

# Mapping between user_id and a SQLAlchemy group object of the
# contacts for that user.
user_contact_group_map = {}

# A mapping between the contact ID of an existing contact, and the
# SQLAlchemy user that now represents that contact.
contact_id_to_user_map = {}

single_user = 482
update_recognition = False

for contact in contacts:
    # DEBUG
    continue

    # Skip groups, we'll handle them below.
    if contact['is_group']:
        continue

    owner_id = contact['owner_id']

    # For ease of debugging.
    if single_user and owner_id != single_user:
        continue

    print "Working on user:", owner_id

    owner = orm.query( Users ).filter( Users.id == owner_id ).one()
    
    contact_group = None

    if owner_id in user_contact_group_map:
        contact_group = user_contact_group_map[owner_id]
    else:
        contact_group = Groups( uuid       = str( uuid.uuid4() ),
                                group_type = 'contact',
                                group_name = 'Contacts' )
        user_contact_group_map[owner_id] = contact_group
        owner.groups.append( contact_group )
        print "\tCreating new contact_group:", contact_group.uuid

    contact_email = contact['contact_email']

    existing_users = []
    existing_user = None
    
    if contact_email is not None:
        existing_users = orm.query( Users ).filter( Users.email == contact_email )[:]

    if len( existing_users ) == 1:
        existing_user = existing_users[0]
    elif len( existing_users ) > 1:
        print "\tERROR! MULTIPLE USERS FOUND FOR EMAIL: %s" % ( contact_email )
        orm.rollback()
        continue
    else:
        existing_user = Users( uuid        = str( uuid.uuid4() ),
                               provider    = contact['provider'],
                               provider_id = contact['provider_id'],
                               email       = contact_email,
                               displayname = contact['contact_name'],
                               user_type   = 'contact' )
        print "\tCreating new user:", existing_user.uuid
        
    contact_id_to_user_map[contact['id']] = existing_user

    new_contact = UserGroups( uuid        = str( uuid.uuid4() ),
                              member_name = contact['contact_name'],
                              member_role = 'contact',
                              picture_uri = contact['picture_uri'] )
    print "\tCreating new contact:", new_contact.uuid

    existing_user.user_groups.append( new_contact )
    contact_group.user_groups.append( new_contact )
    
    print "\tBuilding associations between o:%s g:%s c:%s" % ( owner.id, contact_group.uuid, new_contact.uuid )

    mafs = orm.query( MediaAssetFeatures ).filter( MediaAssetFeatures.contact_id == contact['id'] )

    maf_ids = []

    for maf in mafs:
        print "\tAssigning media_asset_feature %s to user %s not contact %s" % ( maf.id, existing_user.uuid, maf.contact_id )
        existing_user.media_asset_features.append( maf )
        maf_ids.append( maf.id )

    print "\tCommitting"
    orm.commit()

    if update_recognition:
        print "\tAdjusting Recognition"
        vib.cv.FaceRecognition.UIInterface.move_faces( owner_id, contact['id'], existing_user.id, maf_ids )

    print "\tDONE"

# FOR CONTACTS WITH IS_GROUP == 1

# 4. For each sharing group, create a new group of type share.
# 5. Populate the members of the share group with the members of contacts.

f = open( "share_groups.txt" )
share_groups = pickle.load( f )
f.close()

# Keys are contact_groups, values are a list of contact_ids for those groups.
contact_group_id_to_contacts = {}

# Contact group ID to SQLAlchemy share group object
contact_group_id_to_share_group_map = {}

for share_group in share_groups:
    if share_group['group_id'] not in contact_group_id_to_contacts:
        contact_group_id_to_contacts[share_group['group_id']] = [ share_group['contact_id'] ]
    else:
        contact_group_id_to_contacts[share_group['group_id']].append( share_group['contact_id'] )

for contact in contacts:
    # DEBUG
    continue

    # We already handled all contacts that are not groups.
    if not contact['is_group']:
        continue

    owner_id = contact['owner_id']

    # For ease of debugging.
    if single_user and owner_id != single_user:
        continue

    print "Working on user:", owner_id

    owner = orm.query( Users ).filter( Users.id == owner_id ).one()

    share_group = Groups( uuid       = str( uuid.uuid4() ),
                          group_type = 'share',
                          group_name = contact['contact_name'] )
    owner.groups.append( share_group )
    contact_group_id_to_share_group_map[contact['id']] = share_group
    print "\tCreating new share_group:", share_group.uuid    
    
    if contact['id'] in contact_group_id_to_contacts:
        for contact_share_id in contact_group_id_to_contacts[contact['id']]:
            if contact_share_id not in contact_id_to_user_map:
                orm.rollback()
                raise Exception( "Couldn't find user for contact %s" % ( contact_share_id ) )

            shared_to_user = contact_id_to_user_map[contact_share_id]                     

            user_share = UserGroups( uuid        = str( uuid.uuid4() ),
                                     member_name = shared_to_user.displayname,
                                     member_role = 'editor' )
                                 
            print "\tAdding %s to share group" % ( shared_to_user.id )
            shared_to_user.user_groups.append( user_share )
            share_group.user_groups.append( user_share )

    orm.commit()
    print "\tDONE"


# Get information about existing communities
# 
# id
# user_id
# uuid
# name
# webhook
# members_id
# media_id
# curators_id
# pending_id
# is_curated

f = open( "communities.txt" )
communities = pickle.load( f )
f.close()

# For each community, replicate the share to shared_album_groups using
# the share_groups created above.

for community in communities:
    # DEBUG
    continue

    # For ease of debugging.
    if single_user and community['user_id'] != single_user:
        continue

    members_id = community['members_id']
    curators_id = community['curators_id']

    if members_id is None:
        raise Exception( "Null members_id for community: %s" % ( community ) )

    if members_id not in contact_group_id_to_share_group_map:
        raise Exception( "No share group for contact_group_id %s" % ( members_id ) )
    else:
        members_id = contact_group_id_to_share_group_map[members_id].id

    if curators_id in contact_group_id_to_share_group_map:
        curators_id = contact_group_id_to_share_group_map[curators_id].id
    else:
        if curators_id is not None:
            raise Exception( "No share group for contact_group_id %s" % ( members_id ) )
        
    shared_album_group = SharedAlbumGroups( user_id     = community['user_id'],
                                            uuid        = str( uuid.uuid4() ),
                                            name        = community['name'],
                                            share_type  = 'private',
                                            media_id    = community['media_id'],
                                            pending_id  = community['pending_id'],
                                            members_id  = members_id,
                                            curators_id = curators_id,
                                            is_curated  = community['is_curated'],
                                            webhoox     = community['webhook'] )

    orm.add( shared_album_group )

    print "Creating SharedAlbumGroup %s with media %s and members %s" % ( shared_album_group.uuid, community['media_id'], members_id )

    orm.commit()
    print "\tDONE"

# Get information about existing media_shares.
# 
# id
# uuid
# media_id
# user_id
# contact_id
# share_type
# is_group_share
# view_count

f = open( "media_shares.txt" )
media_shares = pickle.load( f )
f.close()

# 1. For all public shares, create a new singleton public share with a singleton album.
# 2. For the other shares, test if there is an existing share group, if so use it.

# Potential shares -> single file shares (these records allow the URLs to be visited)
#
# Hidden shares -> single file shares that someone has viewed - we ignore these.
#
# Public shares -> single file shares (these are to FB, twitter, etc.)
#
# Private shares onto albums are ignored - these are artifacts of how
# new users are created when a community is shared with a non-user
# today.
#
# Private shares onto single files -> single user share group and single album file.
#  display_album = false.

# Key is owner_id
#
# Value is a hash of key member_id value SQLAlchemy object of the
# singleton share group for that user.
user_id_group_map = {}

for media_share in media_shares:
    # DEBUG
    continue

    print "Working on media_share: %s" % ( media_share['id'] )

    media = orm.query( Media ).filter( Media.id == media_share['media_id'] ).one()

    if single_user and single_user != media.user_id:
        continue
    
    # Fix view counts.
    media_view_count = 0
    if media.view_count is not None:
        media_view_count = media.view_count
        
    media_share_view_count = media_share.get( 'view_count', 0 )
    
    if media_share_view_count > media_view_count:
        media.view_count = media_share_view_count

    share_type = media_share['share_type']

    # Ignore hidden shares.
    if share_type == 'hidden':
        print "\tHidden share - skipping."
        continue

    # Ignore this type of private share.
    if share_type == 'private' and media.is_album:
        print "\tPrivate album share - skipping."
        continue

    # Handle the rest.
    if share_type in [ 'public', 'potential' ]:
        # Single file share, just cram it into shared_album_groups.
        sag = SharedAlbumGroups( user_id    = media.user_id,
                                 uuid       = str( uuid.uuid4() ),
                                 share_type = share_type,
                                 media_id   = media.id,
                                 is_curated = False )
        orm.add( sag )

        print "\tAdded single file %s share for media_id %s user %s." % ( share_type, media.id, media.user_id )
    elif share_type == 'private':
        # Create an album to hold the video.
        album = Media( user_id = media.user_id,
                       uuid = str( uuid.uuid4() ),
                       media_type = 'original',
                       is_album = True,
                       display_album = False,
                       is_viblio_created = True )
        media_album = MediaAlbums( media_id = media.id )
        album.media_albums.append( media_album )

        # Create a share group to hold the user.
        share_group = None
        if media.user_id in user_id_group_map:
            if media_share['user_id'] in user_id_group_map[media.user_id]:
                share_group = user_id_group_map[media.user_id][media_share['user_id']]
                print "\tAdding private share to existing group: %s" % ( share_group.id )
            else:
                share_group = Groups( owner_id   = media.user_id,
                                      uuid       = str( uuid.uuid4() ),
                                      group_type = 'share' )
                user_share = UserGroups( member_id   = media_share['user_id'],
                                         uuid        = str( uuid.uuid4() ),
                                         member_role = 'editor' )
                share_group.user_groups.append( user_share )
                user_id_group_map[media.user_id][media_share['user_id']] = share_group
                print "\tAdding private share to new group,user_group: %s, %s" % ( share_group.uuid, user_share.uuid )
        else:
            share_group = Groups( owner_id   = media.user_id,
                                  uuid       = str( uuid.uuid4() ),
                                  group_type = 'share' )
            user_share = UserGroups( member_id   = media_share['user_id'],
                                     uuid        = str( uuid.uuid4() ),
                                     member_role = 'editor' )
            share_group.user_groups.append( user_share )
            user_id_group_map[media.user_id] = { media_share['user_id'] : share_group }                
            print "\tAdding private share to new group,user_group: %s, %s" % ( share_group.uuid, user_share.uuid )

        sag = SharedAlbumGroups( user_id    = media.user_id,
                                 uuid       = str( uuid.uuid4() ),
                                 share_type = share_type,
                                 is_curated = False )
        orm.add( sag )
        album.shared_album_media.append( sag )
        share_group.shared_album_group_members.append( sag )

    orm.commit()
    print "\tDONE"


# Put all user videos in their special 'My Videos' album.
f = open( "media.txt" )
media_shares = pickle.load( f )
f.close()

# media_id
# user_id

user_id_to_user_map = {}
user_id_to_album_map = {}

for m in media_shares:
    if single_user and single_user != m['user_id']:
        continue

    user = None

    if m['user_id'] in user_id_to_user_map:
        user = user_id_to_user_map[m['user_id']]
    else:
        user = orm.query( Users ).filter( Users.id == m['user_id'] ).one()
        
    media = orm.query( Media ).filter( Media.id == m['id'] ).one()

    print "Working on media %s for user %s" % ( media.id, user.id )

    all_video_album = None

    if user.id in user_id_to_album_map:
        all_video_album = user_id_to_album_map[user.id]
    else:
        # Check of this user has the special album:
        all_videos = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.is_viblio_created == True, Media.title == 'My Videos' ) )[:]
            
        if len( all_videos ) == 0:
            all_video_album = Media( user_id = user.id,
                                     uuid = str( uuid.uuid4() ),
                                     media_type = 'original',
                                     is_album = True,
                                     display_album = True,
                                     title = 'My Videos',
                                     is_viblio_created = True )
            orm.add( all_video_album )
            user_id_to_album_map[user.id] = all_video_album
            print "\tCreating all video album: %s" % ( all_video_album.uuid ) 
        elif len( all_videos ) == 1:
            all_video_album = all_videos[0]
            user_id_to_album_map[user.id] = all_video_album
        else:
            print "WHAT?"
            sys.exit( 0 )

    media_album_row = MediaAlbums()
    orm.add( media_album_row )
    media.media_albums_media.append( media_album_row )
    all_video_album.media_albums.append( media_album_row )
    orm.commit()
    print "\tDONE"
