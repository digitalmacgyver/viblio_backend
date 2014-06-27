#!/usr/bin/env python

import datetime
import logging
from logging import handlers
import pickle
from sqlalchemy import and_, distinct, func
import time
import uuid

import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

format_string = 'serialize_contacts: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

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

for contact in contacts:
    # Skip groups, we'll handle them below.
    if contact['is_group']:
        continue

    owner_id = contact['owner_id']

    # DEBUG
    if owner_id != 482:
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

    existing_users = orm.query( Users ).filter( Users.email == contact_email )[:]
    existing_user = None

    if existing_users is not None and len( existing_users ) == 1:
        existing_user = existing_users[0]
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

    for maf in mafs:
        print "\tAssigning media_asset_feature %s to user %s not contact %s" % ( maf.id, existing_user.uuid, maf.contact_id )
        existing_user.media_asset_features.append( maf )
        maf.contact_id = None
    
orm.commit()

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
    # We already handled all contacts that are not groups.
    if not contact['is_group']:
        continue

    owner_id = contact['owner_id']

    # DEBUG
    if owner_id != 482:
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
    if community['user_id'] != 482:
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

# DEBUG - we don't know what's going on here, don't change it till we
# understand it better.

# DEBUG - set media.view_count = media_shares.view_count.
'''

f = open( "media_shares.txt" )
media_shares = pickle.load( f )
f.close()

# 1. For all public shares, create a new singleton public share with a singleton album.
# 2. For the other shares, test if there is an existing share group, if so use it.

# Key is owner_id
#
# Value is a hash of key member_id value SQLAlchemy object of the
# singleton share group for that user.
user_id_group_map = {}

for media_share in media_shares:
    if media_share['user_id'] is None and media_share['share_type'] not in [ 'public', 'potential' ]:
        log.warn( json.dumps( 'message' : "WARNING - no user_id for private or hidden share - skipping: %s" % ( media_share ) ) )
        continue

    media = orm.query( Media ).filter( Media.id == media_share.media_id ).one()

    
    if media_share['user_id'] is None:
        
'''    
    
