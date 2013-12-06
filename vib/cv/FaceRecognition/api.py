import logging

# DEBUG - the caller of this script should define a logger that is
# vib.cv.FaceRecognize so this logger inherits those properties.
log = logging.getLogger( __name__ )

import vib.rekog.utils as rekog
import vib.cv.FaceRecognition.db_utils as recog_db

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

# Within the API: inbound can either be fully formed faces, or hashes
# with a face_id.  We always return fully formed faces.
#
# Each function in this module takes in an array of faces to operate
# on, the structure of a face is a dictionary like object with these
# fields:
# 
# Note: user_id, contact_id, and face_id must be unique across all
# faces added to the system.
#
# user_id - integer identifying the user for this operation - this
# defined a context or namespace for operations.
#
# contact_id - integer identifying the person or contact in the
# external system related to this operation.  In the case of
# move_faces this is the destination.
#
# face_id - integar identifying the particular image for the contact
# in the external system.
#
# face_url - a URL to an image of the face
#
# face_score - A floating point value, for the face in question, given
# a set of faces for the same contact the one with the highest
# face_score will be treated as the "best" image available.
#
# external_id - Optional, an aribitrary integer the external system
# can set to further identify this face in the external system (if
# user_id, contact_id, and face_id are not sufficient)
#
# The return value for each function will be a hash with the following
# keys:
#
# added
# deleted
# moved
# not_found
# error
#
# Each key's value is an array of the input face data structure, and
# in the case of the added, deleted, or moved operations each face
# data structure will also contain a new field called: 'id' which is
# an integer that uniquely identifies this face in the FaceRecognition
# system.
#
# Note: Other fields may be present in the return values, and the
# return values are dictionary like objects, they may not be
# dictionaries.

def delete_contact( user_id, contact_id ):
    '''Deletes all information in the Recognition system about the
    given contact_id, if any.'''

    try:
        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Deleting contact %s for user %s.' % ( contact_id, user_id )
                } )
        
        l1_user_id = "%s_%s" % ( user_id, contact_id )

        faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

        delete_tags = {}

        for face in faces:
            if face.is_face:
                if face.l1_id is not None:
                    if face.l1_tag is not None:
                        tag = face.l1_tag
                    else:
                        tag = '_x_all'

                log.debug( {
                        'user_id'    : user_id,
                        'contact_id' : contact_id,
                        'message'    : 'Adding tag %s with index %s to list of faces to delete in l1 database for %s.' % ( tag, face.l1_id, user_id )
                        } )

                if tag in delete_tags:
                    delete_tags[tag] += ';%s' % ( face.l1_id )
                else:
                    delete_tags[tag] = [ face.l1_id ]
                
        for tag in sorted( delete_tags.keys() ):
            result = rekog.delete_face_for_user( l1_user_id, tag, delete_tags[tag], config.recog_l1_namespace )
            log.debug( {
                    'user_id'    : user_id,
                    'contact_id' : contact_id,
                    'rekog_result' : result,
                    'message'    : 'Deleted faces %s for user_id %s, tag %s' % ( delete_tags[tag], user_id, tag )
                    } )

        result = rekog.train_for_user( l1_user_id, config.recog_l1_namespace )
        log.debug( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'rekog_result' : result,
                'message'    : 'Trained l1 database %s for user_id %s' % ( l1_user_id, user_id )
                } )

        result = rekog.delete_user( user_id, config.recog_l2_namespace )
        log.debug( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'rekog_result' : result,
                'message'    : 'Deleted l2 database for user_id %s' % ( user_id )
                } )
    
        recog_db._delete_contact_faces_for_user( user_id, contact_id )

        return { 
            'added'     : [],
            'deleted'   : faces,
            'moved'     : [],
            'not_found' : [],
            'error'     : []
            }

    except Exception as e:
        log.error( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Error while deleting contact: %s' % ( e )
                } )
        raise

def delete_faces_for_contact( user_id, contact_id, faces ):
    '''Given a user_id, contact_id, and array of faces, delete the
    (partial) faces data structures present in the array.

    The faces array can contain either:

    * Face data structures returned by the methods of this api, or
    * Dictionary like objects with an id field
    '''

    try:
        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Deleting faces related to contact %s for user %s.' % ( contact_id, user_id )
                } )

        deleted = []
        ( faces, not_found, error ) = _get_faces( user_id, contact_id, faces )

        l1_user_id = "%s_%s" % ( user_id, contact_id )

        '''
        For each thing in faces:
        1. Delete all l1 faces for this contact.
        2. Delete all faces from l2
        3. Cluster l2
        4. CROSS CHECK CLUSTER BETWEEN FACES AND DB.
        4. Create new l1 faces from cluster
        5. Retrain l1
        6. Delete face rows from database.
        '''
        
        '''
        Need a "sync" function that sycnrhonizes state of DB from
        state of rekognition.
        L2:
        * Updates cluster tags in DB
        * Removes rows that are is_face but not in rekognition.
        * Deletes rekog stuff that are idx but not in database.
        * Re-clusters (and re-runs to validate)
        L1: ...

        If things have gotten out of sync, then there was either a
        partial update or partial delete.

        * Add order: Rekog then DB.
        * Delete order: Rekog then DB.
        
        So, if something is in Rekog but not the DB, we know there was
        a partial add.

        If something is in the DB but not Rekog, then we know there
        was a partial delete.

        If present in Rekog but not DB, partial add.

        If present in DB and not in Rekog, then partial delete, delete from DB.

        
        '''

        delete_tags = {}

        # DEBUG - check on
        
        for face in faces:
            try:
                if face['l1_idx'] is not None:
                    if face['l1_tag'] is None:
                        tag = '_x_all'
                    else:
                        tag = face['l1_tag']

            log.debug( {
                    'user_id'    : user_id,
                    'contact_id' : contact_id,
                    'message'    : 'Adding tag %s with index %s to list of faces to delete in l1 database for %s.' % ( tag, face.l1_id, user_id )
                    } )

            if tag in delete_tags:
                delete_tags[tag] += ';%s' % ( face.l1_id )
            else:
                delete_tags[tag] = [ face.l1_id ]
                                


                        
                        

                else:
                    raise Exception("Must include id field in face dictionary.")

            except Exception as e:
                # Do not throw exception here - we want to delete as
                # much as we are able to.
                log.info( {
                        'user_id'    : user_id,
                        'contact_id' : contact_id,
                        'message'    : 'Error deleting face for to contact %s for user %s, error was: %s' % ( contact_id, user_id, e )
                } )    
                error.append( face )
                
        faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

        delete_tags = {}

        for face in faces:
            if face.l1_id is not None:
                if face.l1_tag is not None:
                    tag = face.l1_tag
                else:
                    tag = '_all_x'

            log.debug( {
                    'user_id'    : user_id,
                    'contact_id' : contact_id,
                    'message'    : 'Adding tag %s with index %s to list of faces to delete in l1 database for %s.' % ( tag, face.l1_id, user_id )
                    } )

            if tag in delete_tags:
                delete_tags[tag] += ';%s' % ( face.l1_id )
            else:
                delete_tags[tag] = [ face.l1_id ]
                
        for tag in sorted( delete_tags.keys() ):
            result = rekog.delete_face_for_user( user_id, tag, delete_tags[tag], config.recog_l1_namespace )
            log.debug( {
                    'user_id'    : user_id,
                    'contact_id' : contact_id,
                    'rekog_result' : result,
                    'message'    : 'Deleted faces %s for user_id %s, tag %s' % ( delete_tags[tag], user_id, tag )
                    } )

        result = rekog.train_for_user( user_id, config.recog_l1_namespace )
        log.debug( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'rekog_result' : result,
                'message'    : 'Trained l1 database for user_id %s' % ( user_id )
                } )

        result = rekog.delete_user( face.user_id, config.recog_l2_namespace )
        log.debug( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'rekog_result' : result,
                'message'    : 'Deleted l2 database for user_id %s' % ( user_id )
                } )
    
        recog_db._delete_contact_faces_for_user( user_id, contact_id )

        return { 
            'added'     : [],
            'deleted'   : deleted,
            'moved'     : [],
            'not_found' : [],
            'error'     : error
            }

    except Exception as e:
        log.error( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Error while deleting contact: %s' % ( e )
                } )
        raise

def move_faces():
    pass

def add_faces_for_contact():
    pass


def _get_faces( user_id, contact_id, faces ):
    '''Given an input arry of faces, returns an output array of fully
    populated face data structures.'''

    result = []
    errors = []
    not_found = []

    for face in faces:
        # Check if this is already a face data structure
        face_keys = [ 'id', 'user_id', 'contact_id', 'face_id', 'face_url', 'external_id', 'score', 'is_face', 'l1_id', 'l1_tag', 'l2_id', 'l2_tag' ]
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
                    not_found.append( face )
            else:
                errors.append( face )
        else:
            result.append( face )

    return ( result, not_found, errors )
