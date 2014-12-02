import json
import logging

# The caller of this script should define a logger that is
# vib.cv.FaceRecognize so this logger inherits those properties.
log = logging.getLogger( __name__ )

import vib.rekog.utils as rekog
import vib.cv.FaceRecognition.db_utils as recog_db

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

def _reconcile_db_rekog( user_id, contact_id ):
    '''Reconcile the contents of our database and what is in
    ReKognition for a given user and contact.

    Returns true if this method trained recognition as a result of
    alterations.

    There are two conditions to check:
 
    1. A face is present in ReKognition without a corresponding entry
    in the database: delete the face in ReKognition and retrain.

    2. A face is present in the database but not in
    ReKognition. Delete the face from the database.
    '''

    train = False

    db_faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

    all_faces = rekog.visualize_for_user( user_id, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_v2_namespace )

    contact_faces = []

    for face in all_faces:
        try:
            face_contact_id = int( face['tag'] )
        except Exception as e:
            # Either there was no 'tag' in face, or the tag wasn't an int.
            if 'tag' in face:
                log.error( json.dumps( { 'user_id'    : user_id,
                                         'message'    : 'Invalid tag found, tag must be integer, skipping. Face was: %s' % ( face ) } ) )
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'message'    : 'Deleting faces with invalid tag: %s for user_id: %s' % ( face['tag'], user_id ) } ) )
                rekog.delete_face_for_user( user_id, face['tag'], namespace=config.recog_v2_namespace )
            else:
                log.error( json.dumps( { 'user_id'    : user_id,
                                         'message'    : 'Invalid face returned from ReKognition, skipping, face was: %s' % ( face ) } ) )
                
            # Move on to the next face.
            continue
                
        if face_contact_id == contact_id:
            contact_faces.append( face )
            
    log.info( json.dumps( { 'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : "Reconciling DB for u:%s c:%s" % ( user_id, contact_id ) } ) )
    log.info( json.dumps( { 'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : "contact_faces are: %s" % ( contact_faces ) } ) )

    train = _delete_rekog_mismatch( user_id, contact_id, db_faces, contact_faces )

    if train:
        # In this case the above call to _delete_rekog_mismatch
        # altered the contents of ReKognition, so we need to
        # regenerate our list of faces present in ReKognition before
        # proceeding.
        all_faces = rekog.visualize_for_user( user_id, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_v2_namespace )
        contact_faces = []
        for face in all_faces:
            try:
                face_contact_id = int( face['tag'] )
            except Exception as e:
                # Either there was no 'tag' in face, or the tag wasn't an int.
                if 'tag' in face:
                    log.error( json.dumps( { 'user_id'    : user_id,
                                             'message'    : 'Invalid tag found, tag must be integer, skipping. Face was: %s' % ( face ) } ) )
                    log.info( json.dumps( { 'user_id'    : user_id,
                                            'message'    : 'Deleting faces with invalid tag: %s for user_id: %s' % ( face['tag'], user_id ) } ) )
                    rekog.delete_face_for_user( user_id, face['tag'], namespace=config.recog_v2_namespace )
                else:
                    log.error( json.dumps( { 'user_id'    : user_id,
                                             'message'    : 'Invalid face returned from ReKognition, skipping, face was: %s' % ( face ) } ) )
                
                # Move on to the next face.
                continue

            if face_contact_id == contact_id:
                contact_faces.append( face )

    _delete_db_mismatch( user_id, contact_id, db_faces, contact_faces )

    if train:
        result = rekog.train_for_user_contact( user_id, contact_id, config.recog_v2_namespace )
        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'rekog_result' : result,
                                 'message'    : 'RECONCILE Trained recognition for user_id %s' % ( user_id ) } ) )

    return train

def _delete_db_mismatch( user_id, contact_id, db_faces, contact_faces ):
    '''Finds any records in the database that indicate a face present
    in a ReKognition system, but which are not actually present in
    ReKognition.

    Delete the face in question when this happens.
    '''

    rec_indices = {}
    
    for face in contact_faces:
        for idx in face['index']:
            rec_indices[idx] = True

    for face in db_faces:
        if face['idx'] not in rec_indices:
            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : "RECONCILIATION Deleting db only face: %s" % ( _format_face( face ) ) } ) )
            recog_db._delete_faces( [ face ] )

    return

def _delete_rekog_mismatch( user_id, contact_id, db_faces, contact_faces ):
    '''Finds any faces in ReKognition which are not present in the
    database, and deletes them from ReKognition.

    Returns true if any faces were deleted from ReKognition.'''
    
    deleted = False

    # Build a hash of the database's view of the faces in ReKognition
    # with:
    # Key = the ReKognition ID of the face
    db_indices = {}
    for face in db_faces:
        db_indices[face['idx']] = True

    # Cross check ReKognition's view with the DB.
    for face in contact_faces:
        for idx in face['index']:
            if idx not in db_indices:
                deleted = True
                result = rekog.delete_face_for_user( user_id, face['tag'], idx, namespace=config.recog_v2_namespace )
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "RECONCILIATION Deleted Recog only face with idx: %s tag: %s" % ( idx, face['tag'] ) } ) )

    return deleted

def _populate_faces( user_id, contact_id, faces ):
    '''Given an input array of faces, returns an output array of fully
    populated face data structures.'''

    result = []
    unchanged = []
    errors = []

    face_keys = [ 'id', 'user_id', 'contact_id', 'face_id', 'face_url', 'external_id', 'idx' ]

    for face in faces:
        # Check if this is already a face data structure
        valid_face = True
        for key in face_keys:
            if key not in face:
                valid_face = False
                break
        if not valid_face:
            if 'id' in face:
                f = recog_db._get_face_by_id( face['id'] )
                if f is not None:
                    result.append( f )
                else:
                    unchanged.append( face )
            else:
                errors.append( face )
        else:
            result.append( face )

    return ( result, unchanged, errors )

def _format_face( face ):
    '''Utility to produce a nice string from a face.'''
    return "i:%s u:%s c:%s f:%s idx:%s" % ( face.get( 'id', 'N/A' ), face['user_id'], face['contact_id'], face['face_id'], face.get( 'idx', 'N/A' ) )

