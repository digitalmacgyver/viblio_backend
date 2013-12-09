import logging

# DEBUG - the caller of this script should define a logger that is
# vib.cv.FaceRecognize so this logger inherits those properties.
log = logging.getLogger( __name__ )

import vib.rekog.utils as rekog
import vib.cv.FaceRecognition.db_utils as recog_db
import vib.cv.FaceRecognition.helpers as helpers

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

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
# score - A floating point value, for the face in question, given a
# set of faces for the same contact the one with the highest
# face_score will be treated as the "best" image available.
#
# external_id - Optional, an aribitrary integer the external system
# can set to further identify this face in the external system (if
# user_id, contact_id, and face_id are not sufficient)
#
# The return value for each function will be a hash with the following
# keys:
#
# added, deleted, unchanged, error
#
# Reflecting the disposition of each face from the input.

def add_faces( user_id, contact_id, faces ):
    pass

def delete_contact( user_id, contact_id ):
    '''Deletes all information in the Recognition system about the
    given contact_id, if any.'''

    try:
        # DEBUG - get serialization lock, set locked variable, add
        # finally clause to unlock.

        # DEBUG - decide where to run synchronization to clean stuff
        # up, here, or at the bottom.

        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Deleting contact %s for user %s.' % ( contact_id, user_id )
                } )
        
        l2_user_id = "%s_%s" % ( user_id, contact_id )

        faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

        l1_delete_tags = {}

        for face in faces:
            if face.is_face:
                if face.l1_id is not None:
                    tag = face.l1_tag

                    log.debug( {
                            'user_id'    : user_id,
                            'contact_id' : contact_id,
                            'message'    : 'Adding tag %s with index %s to list of faces to delete in l1 database for %s.' % ( tag, face.l1_id, user_id )
                            } )

                    if tag in l1_delete_tags:
                        l1_delete_tags[tag] += ';%s' % ( face.l1_id )
                    else:
                        l1_delete_tags[tag] = [ face.l1_id ]
                
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
                'message'    : 'Trained l1 database %s for user_id %s' % ( user_id, user_id )
                } )

        result = rekog.delete_user( l2_user_id, config.recog_l2_namespace )
        log.debug( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'rekog_result' : result,
                'message'    : 'Deleted l2 database for user_id %s' % ( l2_user_id )
                } )
    
        recog_db._delete_contact_faces_for_user( user_id, contact_id )

        return { 
            'added'     : [],
            'deleted'   : faces,
            'unchanged' : [],
            'error'     : []
            }

    except Exception as e:
        log.error( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Error while deleting contact: %s' % ( e )
                } )
        raise

def delete_faces( user_id, contact_id, faces ):
    '''Given a user_id, contact_id, and array of faces, delete the
    faces data structures present in the array.

    The faces array can contain either:

    * Face data structures returned by the methods of this api, or
    * Dictionary like objects with an id field
    '''

    try:
        # DEBUG turn on serialization.

        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Deleting faces related to contact %s for user %s.' % ( contact_id, user_id )
                } )

        deleted = []
        ( faces, not_found, error ) = helpers._populate_faces( user_id, contact_id, faces )

        l2_user_id = "%s_%s" % ( user_id, contact_id )

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

def delete_user( user_id ):
    pass

def get_faces( user_id, contact_id = None ):
    pass

def recognize_face( user_id, face_url ):
    pass

