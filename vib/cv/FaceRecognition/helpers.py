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
    ReKognition.

    Returns true if this method trained l1 as a result of alterations
    to l1.

    There are several conditions to check:
 
    1. A face is present in the ReKognition level 2 structure without
    a corresponding entry in the database: delete the face in
    ReKognition.

    2. A face is present in the ReKognition level 1 structure for this
    contact without a corresponding entry in the database: delete the
    face in ReKognition.

    3. A face is present in the database and tagged as having an l2
    entry, but no l2 entry exists in ReKognition: If the face has an
    l1 tag, delete the l2 tags, otherwise delete the face entirely.

    4. A face is present in the database and tagged as having an l1
    entry, but no l1 entry exists in ReKognition: If the face has an
    l2 tag, delete the l1 tag, otherwise delete the face entirely.

    5. A face in l2 has changed its cluster membership: update the
    database to reflect the new cluster.

    6. The clusters in l2 have different l1 candidates than are
    present in the database: delete the offending l1 candidates from
    ReKognition, add the new candidates to ReKognition, update the
    related database rows.

    If any face is deleted from level 2 in any operation, level 2 must
    be reclustered.

    If any face is deleted or added to level 1 in any operation level
    1 must be trained.
    '''

    l1_user = _get_l1_user( user_id )
    l2_user = _get_l2_user( user_id, contact_id )

    l1_train = False
    l2_cluster = False

    db_faces = recog_db._get_contact_faces_for_user( user_id, contact_id )
    all_l1_faces = rekog.visualize_for_user( l1_user, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_l1_namespace )
    l1_faces = []
    for l1_face in all_l1_faces:
        l1_contact_id = int( _parse_l1_tag( l1_face['tag'] )[0] )
        if l1_contact_id == contact_id:
            l1_faces.append( l1_face )
        
    l2_faces = rekog.visualize_for_user( l2_user, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_l2_namespace )

    log.info( json.dumps( { 'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : "Reconciling DB for u:%s c:%s" % ( user_id, contact_id ) } ) )
    log.info( json.dumps( { 'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : "l1_faces are: %s" % ( l1_faces ) } ) )
    log.info( json.dumps( { 'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : "l2_faces are: %s" % ( l2_faces ) } ) )

    # This call may change the contents of the ReKognition system, so
    # we must regenerate the l1_faces and l2_faces data structures.
    ( l1_train, l2_cluster ) = _delete_rekog_mismatch( user_id, contact_id, db_faces, l1_faces, l2_faces )
    if l2_cluster:
        rekog.cluster_for_user( l2_user, config.recog_l2_namespace )
    all_l1_faces = rekog.visualize_for_user( l1_user, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_l1_namespace )
    l1_faces = []
    for l1_face in all_l1_faces:
        l1_contact_id = int( _parse_l1_tag( l1_face['tag'] )[0] )
        if l1_contact_id == contact_id:
            l1_faces.append( l1_face )

    l2_faces = rekog.visualize_for_user( l2_user, num_img_return_pertag=None, no_image=True, show_default=True, namespace=config.recog_l2_namespace )

    # This call may change the contents of the the database, so we
    # must regenerate db_faces
    _delete_db_mismatch( user_id, contact_id, db_faces, l1_faces, l2_faces )
    db_faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

    if _reconcile_clusters( user_id, contact_id, db_faces, l1_faces, l2_faces ):
        l1_train = True

    if l1_train:
        rekog.train_for_user( l1_user, config.recog_l1_namespace )

    return l1_train

def _get_l1_user( user_id ):
    '''Given a user_id, returns the ReKognition user for the l1
    structure for that user.'''

    return "%s" % ( user_id )

def _get_l2_user( user_id, contact_id ):
    '''Given a user_id and a contact_id, returns the ReKognition user
    for the l2 structure for that user and contact.'''

    return "%s_%s" % ( user_id, contact_id )

def _delete_db_mismatch( user_id, contact_id, db_faces, l1_faces, l2_faces ):
    '''Finds any records in the database that indicate a face present
    in a ReKognition system, but which are not present in
    ReKognition.

    Either delete the erroneous layer idx/tag if the face is indeed
    present in another layer, or delete the record entirely.
    '''

    l1_indices = {}
    
    for face in l1_faces:
        for idx in face['index']:
            l1_indices[idx] = face['tag']

    l2_indices = {}

    for face in l2_faces:
        for idx in face['index']:
            l2_indices[idx] = face['tag']

    for face in db_faces:
        l1_idx = face['l1_idx']
        l1_tag = face['l1_tag']
        l2_idx = face['l2_idx']
        l2_tag = face['l2_tag']

        if l1_idx and l1_idx not in l1_indices:
            if l2_idx and l2_idx in l2_indices:
                # This face has invalid l1 settings, but valid l2
                # settings, remove the l1 settings.
                recog_db._update_layer_settings( face, None, None, l2_idx, l2_tag )

                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "DB: Setting l1 values to NULL for: %s" % ( _format_face( face ) ) } ) )
            else:
                # This face has no valid settings, delete the entire
                # record.
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "DB: Deleting face: %s" % ( _format_face( face ) ) } ) )
                recog_db._delete_faces( [ face ] )
        elif l2_idx and l2_idx not in l2_indices:
            if l1_idx and l1_idx in l1_indices:
                recog_db._update_layer_settings( face, l1_idx, l1_tag, None, None )
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "DB: Setting l2 values to NULL for: %s" % ( _format_face( face ) ) } ) )
            else:
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "DB: Deleting face: %s" % ( _format_face( face ) ) } ) )
                recog_db._delete_faces( [ face ] )

    return

def _delete_rekog_mismatch( user_id, contact_id, db_faces, l1_faces, l2_faces ):
    '''Finds any faces in l1 or l2 which are not present in the
    database, and deletes them from ReKognition.

    Returns a tuple of ( Boolean, Boolean ) where the first is true if
    any faces were deleted from l1, and the second is true if any
    faces were deleted from l2.'''

    l1_user = _get_l1_user( user_id )
    l2_user = _get_l2_user( user_id, contact_id )
    
    l1_deleted = False
    l2_deleted = False

    db_l1_indices = {}
    db_l2_indices = {}
    for face in db_faces:
        if face['l1_idx']:
            db_l1_indices[face['l1_idx']] = face['l1_tag']

        if face['l2_idx']:
            db_l2_indices[face['l2_idx']] = face['l2_tag']

    for face in l1_faces:
        for idx in face['index']:
            if idx not in db_l1_indices:
                l1_deleted = True
                result = rekog.delete_face_for_user( l1_user, face['tag'], idx, config.recog_l1_namespace )
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "ReKog: Deleted DB face from L1 idx: %s tag: %s" % ( idx, face['tag'] ) } ) )


    for face in l2_faces:
        for idx in face['index']:
            if idx not in db_l2_indices:
                l2_deleted = True
                result = rekog.delete_face_for_user( l2_user, face['tag'], idx, config.recog_l2_namespace )
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "ReKog: Deleted DB face from L2 idx: %s tag: %s" % ( idx, face['tag'] ) } ) )


    return ( l1_deleted, l2_deleted )

def _populate_faces( user_id, contact_id, faces ):
    '''Given an input array of faces, returns an output array of fully
    populated face data structures.'''

    result = []
    unchanged = []
    errors = []

    face_keys = [ 'id', 'user_id', 'contact_id', 'face_id', 'face_url', 'external_id', 'score', 'l1_idx', 'l1_tag', 'l2_idx', 'l2_tag' ]

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
    return "i:%s u:%s c:%s f:%s l1idx:%s l1tag:%s l2idx:%s l2tag:%s s:%s" % ( face.get( 'id', 'N/A' ), face['user_id'], face['contact_id'], face['face_id'], face.get( 'l1_idx', 'N/A' ), face.get( 'l1_tag', 'N/A' ), face.get( 'l2_idx', 'N/A' ), face.get( 'l2_tag', 'N/A' ), face['score'] )

def _reconcile_clusters( user_id, contact_id, db_faces, l1_faces, l2_faces ):
    '''
    Inputs:

    l1_faces - the current list of all faces in l1.  Each l1 face has
    a tag and an index.  Their tag is the composition of the
    contact_id:l2tag:l2idx that the face is taken from.

    l2_faces - the current list of all faces in l2.  Each l2 face has
    a tag and an index.  Each face participates in the special
    '_x_all' tag, and may participate in exactly one more 'cluster#'
    tag.

    db_faces - The current values stored in the database.  Each face
    present in l1 or l2 is represented in db_faces somewhere.
    db_faces should be correct with regard to the l1tag and l1idx
    values of it's faces, but the l2tag and l2idx values can be
    incorrect as this function is to be called post clustering.
    '''

    l1_user = _get_l1_user( user_id )
    l2_user = _get_l2_user( user_id, contact_id )
    
    # db_face_by_l1_idx[idx] = face
    # db_face_by_l2_idx[idx] = face
    ( db_face_by_l1_idx, db_face_by_l2_idx ) = _prepare_db_face_data( db_faces )

    # l1_face_for_contact_by_idx[l1_idx] = l1_tag
    # l1_face_for_contact_by_l2_idx[l2_idx] = { l1_idx, l2_tag }
    # l1_face_for_contact_by_l2_tag[l2_tag] = { l1_idx, l2_idx }
    ( l1_face_for_contact_by_idx, l1_face_for_contact_by_l2_idx, l1_face_for_contact_by_l2_tag ) = _prepare_l1_face_data( l1_user, contact_id, l1_faces )

    # l2_face_by_idx[idx] = l2_tag
    # best_l2_face[tag] = l2_idx
    # NOTE: best_l2_face does not include faces for the _x_all tag.
    ( l2_face_by_idx, best_l2_face ) = _prepare_l2_face_data( l2_faces, db_face_by_l2_idx )

    # Update the databases tag settings for all faces in l2 which have
    # changed clusters.
    for l2_idx, l2_tag in l2_face_by_idx.items():
        if l2_idx not in db_face_by_l2_idx:
            log.error( "Index %s for tag %s not found in DB l2, but it should be." % ( l2_idx, l2_tag ) )
        elif l2_tag != db_face_by_l2_idx[l2_idx]['l2_tag']:
            face = db_face_by_l2_idx[l2_idx]

            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : "DB: Setting l2 values idx:%s tag:%s  for: %s" % ( l2_idx, l2_tag, _format_face( face ) ) } ) )

            recog_db._update_layer_settings( face, face['l1_idx'], face['l1_tag'], l2_idx, l2_tag )

    # Update the l1 ReKognition system and database wherever l1
    # mappings have changed.
    l1_changed = False
    
    # Remove faces from the l1 system
    for l2_tag, data in l1_face_for_contact_by_l2_tag.items():
        l1_idx = data['l1_idx']
        l1_tag = l1_face_for_contact_by_idx[l1_idx]
        l2_idx = data['l2_idx'] 
        face = db_face_by_l2_idx[l2_idx]
        if ( l2_tag not in best_l2_face ) or ( l2_idx != best_l2_face[l2_tag] ):
            # Either a l2 tag has been eliminated, or the l2 candidate
            # for this tag has changed.  In either case we need to
            # remove the current l1 representative for l2 from l1, and
            # set the l1 fields of the database row for this face to
            # null.
            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : "ReKog: Deleting l1 idx:%s tag:%s" % ( l1_idx, l1_tag ) } ) )

            rekog.delete_face_for_user( l1_user, l1_tag, l1_idx, config.recog_l1_namespace )
            
            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : "DB: NULLING l1 fields for: %s" % ( _format_face( face ) ) } ) )

            # Note - l2_idx and l2_tag may be different from
            # face['l2_idx'], face['l2_tag'] due to other changes
            # above.  In this context the data in ReKognition is
            # authoritative.
            recog_db._update_layer_settings( face, None, None, l2_idx, l2_tag )
            l1_changed = True

    # Add faces to the l1 system
    for l2_tag, l2_idx in best_l2_face.items():
        face = db_face_by_l2_idx[l2_idx]
        url = face['face_url']

        if ( l2_tag not in l1_face_for_contact_by_l2_tag ) or ( l2_idx != l1_face_for_contact_by_l2_tag[l2_tag]['l2_idx'] ):
            # This l2 tag is new, or a best new face has been found.
            # In either case we need to add this l2 face to the l1
            # system, and update the l1 fields of the database row for
            # this face to those of an l1 representative.
            l1_tag = _get_l1_tag( contact_id, l2_tag, l2_idx )
            l1_idx = rekog.add_face_for_user( l1_user, url, l1_tag, config.recog_l1_namespace )
            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : "ReKog: added l1 idx:%s tag:%s" % ( l1_idx, l1_tag ) } ) )

            if l1_idx is not None:
                # Note - l2_idx and l2_tag may be different from
                # face['l2_idx'], face['l2_tag'] due to other changes
                # above.  In this context the data in ReKognition is
                # authoritative.
                log.info( json.dumps( { 'user_id'    : user_id,
                                        'contact_id' : contact_id,
                                        'message'    : "DB: Setting values l1idx:%s l1tag:%s l2idx:%s l2tag:%s for: %s" % ( l1_idx, l1_tag, l2_idx, l2_tag, _format_face( face ) ) } ) )

                recog_db._update_layer_settings( face, l1_idx, l1_tag, l2_idx, l2_tag )
                l1_changed = True

    return l1_changed

def _prepare_l1_face_data( user_id, contact_id, l1_faces ):
    '''Helper function that creates some data structures used by
    _reconcile_clusters'''

    l1_user = _get_l1_user( user_id )

    l1_face_for_contact_by_idx = {}
    l1_face_for_contact_by_l2_idx = {}
    l1_face_for_contact_by_l2_tag = {}

    for face in l1_faces:
        l1_tag = face['tag']
        for idx in face['index']:
            ( l2_contact, l2_tag, l2_idx ) = _parse_l1_tag( l1_tag )

            if contact_id == l2_contact:
                # We've encountered a second tagged version of this
                # users face in l1, this should not happen, clean up
                # the duplicate.
                if l2_tag in l1_face_for_contact_by_l2_tag:
                    log.error( json.dumps( { 'user_id'    : user_id,
                                             'contact_id' : contact_id,
                                             'message'    : "Error, found multiple faces for a single l2_tag in l1.  ReKog: Deleting l1 idx:%s tag:%s" % ( idx, l1_tag ) } ) )
                    rekog.delete_face_for_user( l1_user, l1_tag, idx, config.recog_l1_namespace )
                    continue

                l1_face_for_contact_by_idx[idx] = l1_tag
                l1_face_for_contact_by_l2_idx[l2_idx] = { 'l1_idx' : idx, 'l2_tag' : l2_tag }

                l1_face_for_contact_by_l2_tag[l2_tag] = { 'l1_idx' : idx, 'l2_idx' : l2_idx }

    return ( l1_face_for_contact_by_idx, l1_face_for_contact_by_l2_idx, l1_face_for_contact_by_l2_tag )
            
def _prepare_db_face_data( db_faces ):
    '''Helper function that creates some data structures used by
    _reconcile_clusters'''

    db_face_by_l1_idx = {}
    db_face_by_l2_idx = {}

    for face in db_faces:
        if face['l1_idx']:
            db_face_by_l1_idx[face['l1_idx']] = face
        if face['l2_idx']:
            db_face_by_l2_idx[face['l2_idx']] = face
            
    return ( db_face_by_l1_idx, db_face_by_l2_idx )
            
def _prepare_l2_face_data( l2_faces, db_face_by_l2_idx ):
    '''Helper function that creates some data structures used by
    _reconcile_clusters'''

    l2_face_by_idx = {}
    best_l2_face = {}

    for face in l2_faces:
        l2_tag = face['tag']

        for idx in face['index']:
            # Build up l2_face_by_idx - each face in a cluster also
            # appears in the _x_all tag, we only denote the l2_tag as
            # being _x_all if that is the only occurrence.
            if idx in l2_face_by_idx:
                if l2_tag != '_x_all':
                    l2_face_by_idx[idx] = l2_tag
            else:
                l2_face_by_idx[idx] = l2_tag
            
            # Build up best_l2_face
            if l2_tag != '_x_all':
                if l2_tag not in best_l2_face:
                    best_l2_face[l2_tag] = idx
                else:
                    current_face = db_face_by_l2_idx[idx]
                    best_face = db_face_by_l2_idx[best_l2_face[l2_tag]]
                    if current_face['score'] > best_face['score']:
                        best_l2_face[l2_tag] = idx
                    elif current_face['score'] == best_face['score']:
                        # When the current face has the same score as
                        # the best face so far, break the tie based on
                        # whoever has the lower database ID, this
                        # makes selection of the best face
                        # deterministic.
                        if current_face['id'] < best_face['id']:
                            best_l2_face[l2_tag] = idx

    return ( l2_face_by_idx, best_l2_face )
    
def _get_l1_tag( contact_id, l2_tag, l2_idx ):
    '''Return the l1 tag name for a give contact, l2 tag and index
    index.'''

    return "%s-%s-%s" % ( contact_id, l2_tag, l2_idx )

def _parse_l1_tag( l1_tag ):
    '''Return the tuple: ( contact_id, l2_tag, l2_idx )'''
    
    ( c, t, i ) = l1_tag.split( '-' )

    return ( int( c ), t, i )
