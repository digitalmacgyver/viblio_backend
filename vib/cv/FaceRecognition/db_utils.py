# This is an internal module to FaceRecognition.  The database access
# here is implementation dependent and may change.  These functions
# should only be called by other functions in the
# vib.cv.FaceRecognition namespace.

import logging
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *

# DEBUG - the caller of this script should define a logger that is
# vib.cv.FaceRecognize so this logger inherits those properties.
log = logging.getLogger( __name__ )

def _delete_contact_faces_for_user( user_id, contact_id ):
    '''Deletes all faces associated with this contact from our
    database.  The caller is presumed to have removed any other
    relevant artifacts.'''

    try:

        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Deleting all faces for user_id %s, contact_id %s' % ( user_id, contact_id )
                } )

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces ).filter( and_( Faces.user_id == user_id, Faces.contact_id == contact_id ) ).delete()

        orm.commit()
    
        return

    except Exception as e:
        log.error( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Error deleting all faces for user %s, contact %s: %s' % ( user_id, contact_id, e )
                } )
        raise

def _delete_faces( faces ):
    '''Given an array of faces, deletes them from the database.

    The caller is presumed to have removed any other relavant
    artifacts.'''

    for face in faces:
        orm = None
        try:
            face_id = face['id']
            user_id = face['user_id']
            contact_id = face['contact_id']
            log.info( {
                    'user_id'    : user_id,
                    'contact_id' : contact_id,
                    'message'    : 'Deleting face %s for user_id %s, contact_id %s' % ( face_id, user_id, contact_id )
                    } )

            orm = vib.db.orm.get_session()
    
            query = orm.query( Faces ).filter( Faces.id == face_id ).delete()

            orm.commit()

        except Exception as e:
            log.error( {
                    'message'    : 'Error deleting face, error was: %s' % ( e )
                    } )
            if orm is not None:
                orm.rollback()
            raise

    return

def _get_faces_by_id( face_id ):
    '''Returns either a dictionary like object representing the row
    for in the recognition database for this face, or None if the face
    is not found.'''

    try:

        log.info( {
                'message'    : 'Getting face data for face_id: %s' % ( face_id )
                } )

        orm = vib.db.orm.get_session()
    
        result = orm.query( Faces ).filter( Faces.id == face_id )

        if result.count() == 1:
            return result[0].__dict__
        else:
            return None

    except Exception as e:
        log.error( {
                'message'    : 'Error getting face data, error was: %s' % ( e )
                } )
        raise

def _get_contact_faces_for_user( user_id, contact_id ):
    '''Returns an array of dictionary objects.  The dictionaries have
    keys with column names from the table, and the relevant values.
    The return value also contains interal keys which are not column
    names.'''

    try:

        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Getting list of contacts for user_id %s, contact_id %s' % ( user_id, contact_id )
                } )

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces ).filter( and_( Faces.user_id == user_id, Faces.contact_id == contact_id ) )

        result = [ u.__dict__ for u in query.all() ]
        
        orm.commit()
    
        return result

    except Exception as e:
        log.error( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Error getting list of contacts: %s' % ( e )
                } )
        raise

def _upate_layer_settings( face, l1_idx, l1_tag, l2_idx, l2_tag ):
    '''Update the l1/l2 settings for the face in question'''

    orm = None
    try:
        face_id = face['id']
        user_id = face['user_id']
        contact_id = face['contact_id']
        log.info( {
                'user_id'    : user_id,
                'contact_id' : contact_id,
                'message'    : 'Updating face_id %s with l1_idx-tag: %s-%s and l2_idx-tag: %s-%s' % ( face_id, l1_idx, l1_tag, l2_idx, l2_tag )
                } )

        orm = vib.db.orm.get_session()
    
        face = orm.query( Faces ).filter( Face.id == face_id )[0]

        face.l1_idx = l1_idx
        face.l1_tag = l1_tag
        face.l2_idx = l2_idx
        face.l2_tag = l2_tag
        
        orm.commit()

        return

    except Exception as e:
        log.error( {
                'message'    : 'Error updating face l1/2 data: %s' % ( e )
                } )
        raise
