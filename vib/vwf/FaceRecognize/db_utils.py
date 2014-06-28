#!/usr/bin/env python

import json
import logging
from sqlalchemy import and_, func, distinct
import uuid

import vib.cv.FaceRecognition.api as rec
import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

def get_user_id( user_uuid ):
    '''inputs: a user_uuid string

    outputs: the numeric id of that user.'''

    log.debug( json.dumps( { 'user_uuid' : user_uuid,
                             'message' : 'Getting user_id for user_uuid %s' % user_uuid } ) ) 

    orm = vib.db.orm.get_session()

    user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

    return user.id

def update_media_status( media_uuid, status ):
    '''Update the status of the media_uuid in question'''
    orm = vib.db.orm.get_session()

    media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]
    
    mwfs = MediaWorkflowStages( workflow_stage = status )
    media.media_workflow_stages.append( mwfs )

    orm.commit()
    return

def contact_exists( contact_id ):
    '''Returns true if the contact in question exists.'''
    orm = vib.db.orm.get_session()

    contacts = orm.query( Contacts ).filter( Contacts.id == contact_id )[:]
    
    result = False
    
    if len( contacts ) == 1:
        result = True

    orm.commit()
    return result

def add_face( user_uuid, media_uuid, track_id, track_face, recognition_result, recognition_confidence ):
    '''For the given user_uuid, media_uuid, track_id, track_face add a
    new contact and face with with the the recognition_result,
    recognition_confidence
    
    Returns the ( face_id, contact_id ) of the added face on success.
    '''
    log.debug( json.dumps( { 'user_uuid' : user_uuid,
                             'media_uuid' : media_uuid,
                             'message' : 'Adding new face in video %s for user %s' % ( media_uuid, user_uuid ) } ) )

    orm = vib.db.orm.get_session()

    try:
        media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]
        media_id = media.id

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]
        user_id = user.id
    except Exception as e:
        message = 'Failed to find media %s or user %s in database, perhaps they have been deleted?' % ( media_uuid, user_uuid )
        log.error( json.dumps( { 'user_uuid' : user_uuid,
                                 'media_uuid' : media_uuid,
                                 'message' : message } ) )
        raise Exception( message )

    try:
        contact_uuid = str( uuid.uuid4() )
        log.info( json.dumps( { 'user_uuid' : user_uuid,
                                'media_uuid' : media_uuid,
                                'contact_uuid' : contact_uuid,
                                'message' : "Creating new contact with uuid %s for user_id %s " % ( contact_uuid, user_id ) } ) )

        new_contact = Contacts( 
            uuid        = contact_uuid, 
            user_id     = user_id,
            picture_uri = track_face['s3_key']
            )

        log.info( json.dumps( { 'user_uuid' : user_uuid,
                                'media_uuid' : media_uuid,
                                'contact_uuid' : contact_uuid,
                                'track_id' : track_id,
                                'message' : "Associating new contact_uuid %s with track_id %d face_id %d" % ( contact_uuid, track_id, track_face['face_id'] ) } ) )

        feature = orm.query( MediaAssetFeatures ).filter( and_( MediaAssets.id == MediaAssetFeatures.media_asset_id, MediaAssets.uri == track_face['s3_key'] ) ).one()

        feature.recognition_result = recognition_result
        feature.recognition_confidence = recognition_confidence
        new_contact.media_asset_features.append( feature )
        
        orm.commit()

        return ( feature.id, new_contact.id )
    except Exception as e:
        log.warning( json.dumps( { 'user_uuid' : user_uuid,
                                   'media_uuid' : media_uuid,
                                   'message' : "Exception in add_face: %s" % e } ) )
        orm.rollback()
        raise

def update_face( user_uuid, media_uuid, track_id, track_face, recognition_result, recognition_confidence, contact_id ):
    '''For the given user_uuid, media_uuid, track_id, track_face, update the recognition_result, recognition_confidence, and contact_id
    
    Returns the face_id of the modified face on success.
    '''
    log.debug( json.dumps( { 'user_uuid' : user_uuid,
                             'media_uuid' : media_uuid,
                             'message' : 'Updating track %s face %s in video %s for user %s' % ( track_id, track_face['face_id'], media_uuid, user_uuid ) } ) )

    orm = vib.db.orm.get_session()

    try:
        media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]
        media_id = media.id

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]
        user_id = user.id
    except Exception as e:
        message = 'Failed to find media %s or user %s in database, perhaps they have been deleted?' % ( media_uuid, user_uuid )
        log.error( json.dumps( { 'user_uuid' : user_uuid,
                                 'media_uuid' : media_uuid,
                                 'message' : message } ) )
        raise Exception( message )

    try:
        if contact_id is not None:
            contact = orm.query( Contacts ).filter( Contacts.id == contact_id ).one()
    except Exception as e:
        message = 'Failed to find contact_id %s perhaps they have been deleted?' % ( contact_id )
        log.error( json.dumps( { 'user_uuid' : user_uuid,
                                 'media_uuid' : media_uuid,
                                 'message' : message } ) )
        raise Exception( message )

    try:
        feature = orm.query( MediaAssetFeatures ).filter( and_( MediaAssets.id == MediaAssetFeatures.media_asset_id, MediaAssets.uri == track_face['s3_key'] ) ).one()

        feature.recognition_result = recognition_result
        feature.recognition_confidence = recognition_confidence
        feature.contact_id = contact_id

        orm.commit()
        return feature.id
    except Exception as e:
        log.warning( json.dumps( { 'user_uuid' : user_uuid,
                                   'media_uuid' : media_uuid,
                                   'message' : "Exception in update_face: %s" % e } ) )
        orm.rollback()
        raise

