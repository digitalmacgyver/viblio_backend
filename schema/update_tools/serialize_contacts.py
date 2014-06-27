#!/usr/bin/env python

import datetime
import logging
from logging import handlers
import pickle
from sqlalchemy import and_, distinct, func
import time

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

# Get information about contacts.
#
# This query yeilds an iterator of triples, each triple is:
# 
# users.id, users.email, contacts object
#
# The contacts object itself has these fields:
# contact_email
# contact_name
# contact_viblio_id
# created_date
# id
# is_group
# picture_uri
# provider
# provider_id
# updated_date
# user_id
# uuid
raw_contacts = orm.query( Users.id, Users.email, Contacts ).filter( Users.id == Contacts.user_id )
contacts = []

for contact in raw_contacts:
    contacts.append( { 
            'owner_id'          : contact[0],
            'owner_email'       : contact[1],
            'contact_email'     : contact[2].contact_email,
            'contact_name'      : contact[2].contact_name,
            'contact_viblio_id' : contact[2].contact_viblio_id,
            'created_date'      : contact[2].created_date,
            'id'                : contact[2].id,
            'is_group'          : contact[2].is_group,
            'picture_uri'       : contact[2].picture_uri,
            'provider'          : contact[2].provider,
            'provider_id'       : contact[2].provider_id,
            'updated_date'      : contact[2].updated_date,
            'user_id'           : contact[2].user_id,
            'uuid'              : contact[2].uuid
            } )

f = open( "contacts.txt", 'wb' );
pickle.dump( contacts, f )
f.close()

# Get information about existing share groups.
# 
# group_id
# contact_id
raw_share_groups = orm.query( ContactGroups )
share_groups = []

for share_group in raw_share_groups:
    share_groups.append( { 
            'group_id'     : share_group.group_id,
            'contact_id'   : share_group.contact_id,
            'created_date' : share_group.created_date,
            'updated_date' : share_group.updated_date
            } )

f = open( "share_groups.txt", 'wb' );
pickle.dump( share_groups, f )
f.close()


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

raw_media_shares = orm.query( MediaShares )
media_shares = []

for media_share in raw_media_shares:
    media_shares.append( {
            'id'             : media_share.id,
            'uuid'           : media_share.uuid,
            'media_id'       : media_share.media_id,
            'user_id'        : media_share.user_id,
            'contact_id'     : media_share.contact_id,
            'share_type'     : media_share.share_type,
            'is_group_share' : media_share.is_group_share,
            'view_count'     : media_share.view_count
            } )

f = open( "media_shares.txt", 'wb' );
pickle.dump( media_shares, f )
f.close()

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

raw_communities = orm.query( Communities )
communities = []

for community in raw_communities:
    communities.append( {
            'id'             : community.id,
            'user_id'        : community.user_id,
            'uuid'           : community.uuid,
            'name'           : community.name,
            'webhook'        : community.webhook,
            'members_id'     : community.members_id,
            'media_id'       : community.media_id,
            'curators_id'    : community.curators_id,
            'pending_id'     : community.pending_id,
            'is_curated'     : community.is_curated,
            } )

f = open( "communities.txt", 'wb' );
pickle.dump( communities, f )
f.close()
