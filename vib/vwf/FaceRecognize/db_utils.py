#!/usr/bin/env python

import json
import logging
from sqlalchemy import and_, func

import vib.cv.FaceRecognition.api as rec
import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

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

    popular_features = orm.query( MediaAssetFeatures.contact_id, func.count( '*' ) ).filter( and_( MediaAssetFeatures.user_id == user.id, MediaAssetFeatures.contact_id is not None ) ).group_by( MediaAssetFeatures.contact_id )[:6]
    
    popular_contact_ids = {}
    for feature in popular_features:
        popular_contact_ids[feature.contact_id] = True

    popular_contacts = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.picture_uri != None, Contacts.id.in_( popular_contact_ids.keys() ) ) ).order_by( Contacts.created_date.desc() ).all()

    recent_contacts = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.picture_uri != None ) ).order_by( Contacts.created_date.desc() )[:6]

    return popular_contacts + recent_contacts

def get_contact_uuid( contact_id ):
    '''inputs: a contact_id integer

    outputs: the uuid of that contact.'''

    log.debug( json.dumps( { 'contact_id' : contact_id,
                             'message' : 'Getting contact_uuid for contact_id %s' % contact_id } ) ) 

    orm = vib.db.orm.get_session()

    contact = orm.query( Contacts ).filter( Contacts.id == contact_id )[0]

    return contact.uuid

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
    media.status = status

    orm.commit()
    return

def update_contacts( user_uuid, media_uuid, recognized_faces, new_faces, bad_tracks, recognition_data):
    '''For the given user_uuid, media_uuid:
    
    For each new_face:
      Add a new contact with the provided uuid
      Associate the media_asset_features for those tracks with that contact
    
    For each recognized_face:
      Verify that the contact still exists (maybe the user merged it)
      Associate the media_asset_features for those tracks with that contact

    For each new or recognized face:
      An input is provided under recognition_data[contact_uuid] = 
      { 'recognize_result' : { new_face, human_recognized, machine_recognized }, 
        'recognize_id' : 123 }

    For each bad tack:
      Updates recognition_result to the string 'bad_track'

    If a contact in recognized_faces no longer exists, we take no
    action for that contact.

    Returns True on success.
    '''

    #import pdb
    #pdb.set_trace()

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
        for element in bad_tracks:
            bad_track = element['track']
            bad_reason = element['reason']
            bad_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.media_id == media_id, MediaAssetFeatures.track_id == bad_track['track_id'] ) )
            for bad_feature in bad_features:
                log.info( json.dumps( {
                            'user_uuid' : user_uuid,
                            'media_uuid' : media_uuid,
                            'message' : "Labeling media_asset_feature.id %d of track %d as a %s track." % ( bad_feature.id, bad_track['track_id'], bad_reason )
                            } ) )
                bad_feature.recognition_result = bad_reason

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
                for feature in new_features:
                    feature.recognition_result = 'new_face'

                orm.commit()
            try:
                if recognition_data is not None and recognition_data[uuid]['recognize_id'] is not None:
                    rec.recognition_feedback( recognition_data[uuid]['recognize_id'], None )
                _add_recognition_faces( orm, user_id, new_contact.id, media_id, tracks )
            except:
                log.error( json.dumps( {'user_uuid' : user_uuid,
                                       'media_uuid' : media_uuid,
                                       'contact_uuid' : uuid,
                                       'track_id' : track['track_id'],
                                       'message' : "Updating recognition system failed: %s" % ( e ) } ) )
                
        # Handle existing contacts
        for uuid, tracks in recognized_faces.items():
            existing_contact = orm.query( Contacts ).filter( Contacts.uuid == uuid )
            if existing_contact.count() == 0:
                log.error( json.dumps( {
                            'user_uuid' : user_uuid,
                            'media_uuid' : media_uuid,
                            'contact_uuid' : uuid,
                            'message' : "Error existing contact %s no longer exists" % uuid
                            } ) )
                continue
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
                    for feature in existing_features:
                        feature.recognition_result = recognition_data[uuid]['recognition_result']

                    orm.commit()
                try:
                    if recognition_data is not None and recognition_data[uuid]['recognize_id'] is not None:
                        rec.recognition_feedback( recognition_data[uuid]['recognize_id'], 1 )
                    _add_recognition_faces( orm, user_id, existing_contact.id, media_id, tracks )
                except Exception as e:
                    log.error( json.dumps( {'user_uuid' : user_uuid,
                                            'media_uuid' : media_uuid,
                                            'contact_uuid' : existing_contact.uuid,
                                            'track_id' : track['track_id'],
                                            'message' : "Updating recognition system failed: %s" % ( e ) } ) )

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
    best totalConfidence'''

    best_score = -1
    picture_uri = None

    for track in tracks:
        for face in track['faces']:
            if face['totalConfidence'] > best_score:
                picture_uri = face['s3_key']
                best_score = face['totalConfidence']

    return picture_uri
        
def _add_recognition_faces( orm, user_id, contact_id, media_id, tracks ):
    '''Helper function that adds all new faces from this track to the
    regonition system.

    Each track has:
    track_id, faces: [array of faces]
    '''

    try:
        if len( tracks ) == 0:
            return

        track_dict = {}
        for track in tracks:
            track_dict[track['track_id']] = True

        face_rows = orm.query( MediaAssets.uri,
                               MediaAssetFeatures.id,
                               MediaAssetFeatures.media_asset_id,
                               MediaAssetFeatures.detection_confidence
                               ).filter( and_( 
                MediaAssets.id == MediaAssetFeatures.media_asset_id,
                MediaAssets.media_id == media_id,
                MediaAssetFeatures.media_id == media_id,
                MediaAssetFeatures.track_id.in_( track_dict.keys() ) ) )
                               
        faces = []
        
        for face in face_rows:
            faces.append( {
                    'user_id'     : user_id,
                    'contact_id'  : contact_id,
                    'face_id'     : face.id,
                    'face_url'    : "%s%s" % ( config.ImageServer, face.uri ),
                    'external_id' : face.media_asset_id,
                    'score'       : face.detection_confidence } )

        rec.add_faces( user_id, contact_id, faces )

        return
    except Exception as e:
        log.error( json.dumps( { 'user_id' : user_id,
                                 'contact_id' : contact_id,
                                 'message' : "Failed to update recognition system, error was: %s" % ( e ) } ) )
        # Do not raise an exception here.


    
    
