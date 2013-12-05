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
                'message'    : 'Error getting list of contacts: %s' % ( e )
                } )
        raise

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
