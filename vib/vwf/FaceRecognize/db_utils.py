#!/usr/bin/env python

import json
import logging
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *

log = logging.getLogger( __name__ )

def get_picture_contacts_for_user_uuid( user_uuid ):
    '''inputs: a user_uuid string

    outputs: an array of Contacts data structures from SQLAlchemy
    related to the input user_uuid who have pictures. Members of
    contacts are accessed through dot notation, not indexing.'''

    log.debug( json.dumps( {
                'user_uuid' : user_uuid,
                'message' : 'Getting contacts with pictures for user %s' % user_uuid
                } ) )

    orm = vib.db.orm.get_session()

    user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]
    result = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.picture_uri != None ) ).order_by( Contacts.created_date.desc() )[:]

    log.info( json.dumps( {
                'user_uuid' : user_uuid,
                'message' : 'User %s had %d contacts with pictures' % ( user_uuid, len( result ) )
                } ) )

    return result

def update_media_status( media_uuid, status ):
    '''Update the status of the media_uuid in question'''
    orm = vib.db.orm.get_session()

    media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]
    media.status = status

    orm.commit()
    return

def update_contacts( user_uuid, media_uuid, recognized_faces, new_faces, bad_tracks ):
    '''For the given user_uuid, media_uuid:
    
    For each new_face:
      Add a new contact with the provided uuid
      Associate the media_asset_features for those tracks with that contact
    
    For each recognized_face:
      Verify that the contact still exists (maybe the user merged it)
      Associate the media_asset_features for those tracks with that contact

    For each bad tack:
      Updates recognition_result to the string 'bad_track'

    If a contact in recognized_faces no longer exists, the entire
    transaction is abandoned and False is returned.

    Returns True on success.
    '''

    log.debug( json.dumps( {
                'user_uuid' : user_uuid,
                'media_uuid' : media_uuid,
                'message' : 'Updating contacts in video %s for user %s' % ( media_uuid, user_uuid )
                } ) )

    orm = vib.db.orm.get_session()

    try:
        media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]
        media_id = media.id

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]
        user_id = user.id

        # Handle bad tracks
        for bad_track in bad_tracks:
            bad_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == bad_track['track_id'] ) )
            for bad_feature in bad_features:
                log.info( json.dumps( {
                            'user_uuid' : user_uuid,
                            'media_uuid' : media_uuid,
                            'message' : "Labeling media_asset_feature.id %d of track %d as a bad track." % ( bad_feature.id, bad_track['track_id'] )
                            } ) )
                bad_feature.recognition_result = 'bad_track'

        # Handle new contacts
        for uuid, tracks in new_faces.items():
            log.info( json.dumps( {
                        'user_uuid' : user_uuid,
                        'media_uuid' : media_uuid,
                        'contact_uuid' : uuid,
                        'message' : "Creating new contact with uuid %s for user_id %s " % ( uuid, user_id )
                        } ) )

            new_contact = Contacts( 
                uuid        = uuid, 
                user_id     = user_id,
                picture_uri = _get_best_picture_uri( tracks )
                )

            for track in tracks:
                log.info( json.dumps( {
                            'user_uuid' : user_uuid,
                            'media_uuid' : media_uuid,
                            'contact_uuid' : uuid,
                            'track_id' : track['track_id'],
                            'message' : "Associating new user %s with track_id %d" % ( uuid, track['track_id'] )
                        } ) )
                new_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == track['track_id'] ) )[:]
                new_contact.media_asset_features.extend( new_features )

        # Handle existing contacts
        for uuid, tracks in recognized_faces.items():
            existing_contact = orm.query( Contacts ).filter( Contacts.uuid == uuid )
            if existing_contact.count() == 0:
                log.warning( json.dumps( {
                            'user_uuid' : user_uuid,
                            'media_uuid' : media_uuid,
                            'contact_uuid' : uuid,
                            'message' : "Error existing contact %s no longer exists" % uuid
                            } ) )
                orm.rollback()
                return False
            else:
                existing_contact = existing_contact[0]
                existing_contact.picture_uri = _get_best_picture_uri( tracks )
                for track in tracks:
                    log.info( json.dumps( {
                                'user_uuid' : user_uuid,
                                'media_uuid' : media_uuid,
                                'contact_uuid' : existing_contact.uuid,
                                'track_id' : track['track_id'],
                                'message' : "Associating existing user %s with track_id %d" % ( existing_contact.uuid, track['track_id'] )
                                } ) )
                    existing_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == track['track_id'] ) )[:]
                    existing_contact.media_asset_features.extend( existing_features )

        orm.commit()
    except Exception as e:
        log.warning( json.dumps( {
                    'user_uuid' : user_uuid,
                    'media_uuid' : media_uuid,
                    'message' : "Exception in update_contacts: %s" % e
                    } ) )
        orm.rollback()
        raise

    return True

def _get_best_picture_uri( tracks ):
    '''Helper function, run through tracks and return the URI with the
    best face_confidence'''

    best_score = -1
    picture_uri = None

    for track in tracks:
        for face in track['faces']:
            if face['face_confidence'] > best_score:
                picture_uri = face['s3_key']
                best_score = face['face_confidence']

    return picture_uri
        

    
