#!/usr/bin/env python

import datetime
import json
import logging
from optparse import OptionParser
from sqlalchemy import and_, func, not_, or_
import sys
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *

log = logging.getLogger( 'vib.utils.rescue_orphan_faces' )
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

def update_orphan_faces( hours=24*3 ):
    '''Search our database for media_asset_features that are faces,
    and not part of bad tracks, but which are not associated with a
    contact.

    Create a new undefined contact for each track with such a face,
    and assign that face to the contact.'''
    
    try:
        orm = None
        orm = vib.db.orm.get_session()

        from_when = datetime.datetime.utcnow() - datetime.timedelta( hours=hours )
        
        orphan_faces = orm.query( 
            MediaAssetFeatures.id,
            MediaAssetFeatures.media_asset_id,
            MediaAssetFeatures.user_id,
            MediaAssetFeatures.media_id,
            MediaAssetFeatures.track_id,
            MediaAssets.uri,
            Users.uuid,
            Users.id.label( 'user_id' ),
            func.max( MediaAssetFeatures.detection_confidence )
            ).filter( 
            and_( 
                MediaAssets.id == MediaAssetFeatures.media_asset_id,
                MediaAssets.user_id == Users.id,
                MediaAssetFeatures.user_id == Users.id,
                MediaAssetFeatures.face_user_id == None, 
                MediaAssets.asset_type == 'face',
                MediaAssetFeatures.feature_type == 'face',
                or_( MediaAssetFeatures.recognition_result == None, not_( MediaAssetFeatures.recognition_result.in_( [ 'bad_track', 'bad_face', 'two_face', 'not_face' ] ) ) ),
                MediaAssetFeatures.created_date <= from_when
                ) ).group_by(
                MediaAssetFeatures.media_id,
                MediaAssetFeatures.track_id
                ).all()

        log.debug( json.dumps( { 'message' : "Found %d orphan faces." % len( orphan_faces ) } ) )

        for orphan in orphan_faces:
            user = orm.query( Users ).filter( Users.id == orphan.user_id ).one()

            # First off, get or create a contact_group for this user.
            contact_groups = user.groups.filter( Groups.group_type == 'contact' )[:]
            contact_group = None
            if len( contact_groups ) == 0:
                # We need to create a contact group for this user.
                contact_group = ContactGroups( uuid = str( uuid.uuid4() ),
                                               group_type = 'contact',
                                               group_name = 'Contacts' )
                user.append( contact_group )
            elif len( contact_groups ) > 1:
                log.error( json.dumps( { 'user_uuid' : orphan.uuid,
                                         'message' : "Found multiple contact groups for single user.id %s - there should be only one, mapping to the oldest one: %s" % ( orphan.user_id, contact_groups[0].id ) } ) )
                contact_group = contact_groups[0]
            else:
                contact_group = contact_groups[0]

            contact_user = Users( uuid        = str( uuid.uuid4() ),
                                  user_type   = 'contact' )
            orm.add( contact_user )

            contact_user_group = UserGroups( uuid        = str( uuid.uuid4() ),
                                             member_role = 'contact',
                                             picture_uri = orphan.uri )
            contact_user.user_groups.append( contact_user_group )
            contact_group.user_groups.append( contact_user_group )

            log.debug( json.dumps( {
                        'user_uuid' : orphan.uuid,
                        'media_asset_feature_id' : orphan.id,
                        'message' : "Added user/contact %s/%s for orphan media_id/track_id %s/%s" %  ( contact_user.uuid, contact_user_group.uuid, orphan.media_id, orphan.track_id )
                        } ) )

            faces = orm.query( MediaAssetFeatures ).filter( and_(
                    MediaAssetFeatures.media_id == orphan.media_id,
                    MediaAssetFeatures.track_id == orphan.track_id ) ).all()
            contact_user.media_asset_features.extend( faces )
            log.debug( json.dumps( {
                        'user_uuid' : orphan.uuid,
                        'message' : "Added %d features to user %s for orphan media_id/track_id %s/%s" %  ( len( faces ), contact_user.uuid, orphan.media_id, orphan.track_id )
                        } ) )
            

        orm.commit()

        return True

    except Exception as e:
        if orm != None:
            orm.rollback()
        log.error( json.dumps( {
                    'message' : "Exception was: %s" % e
                    } ) )
        raise
    
if __name__ == '__main__':
    try:
        while update_orphan_faces():
            # Run once every 6 hours
            time.sleep( 6*60*60 )
    except Exception as e:
        log.error( json.dumps( {
                    'message' : "Exception was: %s" % e
                    } ) )
        raise
