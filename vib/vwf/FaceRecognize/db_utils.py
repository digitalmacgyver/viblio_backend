#!/usr/bin/env python

import vib.db.orm
from vib.db.models import *

from sqlalchemy import and_

def get_picture_contacts_for_user_uuid( user_uuid ):
    '''inputs: a user_uuid string

    outputs: an array of Contacts data structures from SQLAlchemy
    related to the input user_uuid who have pictures. Members of
    contacts are accessed through dot notation, not indexing.'''
    orm = vib.db.orm.get_session()

    user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]
    result = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.picture_uri != None ) ).order_by( Contacts.updated_date.desc() )[:]
    return result

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
                bad_feature.recognition_result = 'bad_track'

        # Handle new contacts
        for uuid, tracks in new_faces.items():
            print "Creating new contact with uuid %s for user_id %s " % ( uuid, user_id )
            new_contact = Contacts( 
                uuid        = uuid, 
                user_id     = user_id,
                picture_uri = _get_best_picture_uri( tracks )
                )
            for track in tracks:
                print "Associating %s with track_id %d" % ( uuid, track['track_id'] )
                new_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == track['track_id'] ) )[:]
                new_contact.media_asset_features.extend( new_features )

        # Handle existing contacts
        for uuid, tracks in recognized_faces.items():
            print "Associating these with existing contact.uuid %s: " % uuid
            existing_contact = orm.query( Contacts ).filter( and_( Contacts.uuid == uuid ) )
            if existing_contact.count() == 0:
                print "Error - contact %s did not exist" % uuid
                orm.rollback()
                return False
            else:
                existing_contact = existing_contact[0]
                for track in tracks:
                    print "Associating %s with track_id %d" % ( existing_contact.uuid, track['track_id'] )
                    existing_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == track['track_id'] ) )[:]
                    existing_contact.media_asset_features.extend( existing_features )

        orm.commit()
    except Exception as e:
        print "Exception in update_contacts: %s" % e
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
        

    
