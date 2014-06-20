# This is an internal module to FaceRecognition.  The database access
# here is implementation dependent and may change.  These functions
# should only be called by other functions in the
# vib.cv.FaceRecognition namespace.

import json
import logging
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *

# The caller of this script should define a logger that is
# vib.cv.FaceRecognize so this logger inherits those properties.
log = logging.getLogger( __name__ )

def _add_face( user_id, contact_id, face ):
    '''Inserts a face.'''
    try:
        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'DBUTILS Adding face: %s' % ( face ) } ) )

        orm = vib.db.orm.get_session()

        face = Faces2( 
            user_id     = face['user_id'],
            contact_id  = face['contact_id'],
            face_id     = face['face_id'],
            face_url    = face['face_url'],
            external_id = face['external_id'],
            idx         = face['idx'],
            )

        orm.add( face )
        orm.commit()
    
        return

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error adding faces %s: %s' % ( face, e ) } ) )
        raise        

def _add_recognition_feedback( user_id, face_url, faces ):
    '''Inserts a tracking row for feedback collection'''
    try:
        log.info( json.dumps( { 'user_id'    : user_id,
                                'message'    : 'Adding face recognition feedback row for user %s' % ( user_id ) } ) )

        orm = vib.db.orm.get_session()

        face1_id         = None
        face1_confidence = None
        face2_id         = None
        face2_confidence = None
        face3_id         = None
        face3_confidence = None

        if len( faces ) >= 1:
            face1_id = faces[0]['id']
            face1_confidence = faces[0]['recognition_confidence']
        if len( faces ) >= 2:
            face2_id = faces[1]['id']
            face2_confidence = faces[1]['recognition_confidence']
        if len( faces ) == 3:
            face3_id = faces[2]['id']
            face3_confidence = faces[2]['recognition_confidence']

        feedback = RecognitionFeedback2( 
            user_id          = user_id,
            face_url         = face_url,
            face1_id         = face1_id,
            face1_confidence = face1_confidence,
            face2_id         = face2_id,
            face2_confidence = face2_confidence,
            face3_id         = face3_id,
            face3_confidence = face3_confidence
            )

        orm.add( feedback )
        orm.commit()
    
        return feedback.id

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Error adding recognition feedback row: %s' % ( e ) } ) )
        raise        


def _check_face_exists( user_id, contact_id, face_id ):
    '''Returns true if the given user_id, contact_id, face_id exist in the database.'''
    try:
        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Checking whether user, contact, face_id exists: %s, %s, %s' % ( user_id, contact_id, face_id ) } ) )

        orm = vib.db.orm.get_session()

        result = orm.query( Faces2 ).filter( and_( Faces2.user_id == user_id, Faces2.contact_id == contact_id, Faces2.face_id == face_id ) )[:]

        if len( result ) == 1:
            return True
        elif len( result ) == 0:
            return False
        else:
            raise Exception( "Found %d faces for user, contact, face_id: %s, %s, %s expected 0 or 1." % ( len( result ), user_id, contact_id, face_id ) )

        orm.commit()
    
        return

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error checking whether user, contact, face_id exists %s, %s, %s: %s' % ( user_id, contact_id, face_id, e ) } ) )
        raise        

def _delete_all_user_faces( user_id ):
    '''Given an user_id, deletes all faces pertaining to that user from the database.

    The caller is presumed to have removed any other relevant
    artifacts.'''

    orm = None
    try:
        log.info( json.dumps( { 'user_id'    : user_id,
                                'message'    : 'Deleting all faces for user_id %s' % ( user_id ) } ) )

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces2 ).filter( Faces2.user_id == user_id ).delete()

        orm.commit()

        return
    except Exception as e:
        log.error( json.dumps( { 'message'    : 'Error deleting face, error was: %s' % ( e ) } ) )
        if orm is not None:
            orm.rollback()
            
        raise

def _delete_contact_faces_for_user( user_id, contact_id ):
    '''Deletes all faces associated with this contact from our
    database.  The caller is presumed to have removed any other
    relevant artifacts.'''

    try:

        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Deleting all faces for user_id %s, contact_id %s' % ( user_id, contact_id ) } ) )

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces2 ).filter( and_( Faces2.user_id == user_id, Faces2.contact_id == contact_id ) ).delete()

        orm.commit()
    
        return

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error deleting all faces for user %s, contact %s: %s' % ( user_id, contact_id, e ) } ) )
        raise

def _delete_faces( faces ):
    '''Given an array of faces, deletes them from the database.

    The caller is presumed to have removed any other relevant
    artifacts.'''

    for face in faces:
        orm = None
        try:
            face_id = face['id']
            user_id = face['user_id']
            contact_id = face['contact_id']
            log.info( json.dumps( { 'user_id'    : user_id,
                                    'contact_id' : contact_id,
                                    'message'    : 'Deleting face %s for user_id %s, contact_id %s' % ( face_id, user_id, contact_id ) } ) )

            orm = vib.db.orm.get_session()
    
            query = orm.query( Faces2 ).filter( Faces2.id == face_id ).delete()

            orm.commit()

        except Exception as e:
            log.error( json.dumps( { 'message'    : 'Error deleting face, error was: %s' % ( e ) } ) )
            if orm is not None:
                orm.rollback()
            raise

    return

def _get_all_faces_for_user( user_id ):
    '''Returns an array of dictionary objects.  The dictionaries have
    keys with column names from the table, and the relevant values.
    The return value also contains internal keys which are not column
    names.'''

    try:
        '''
        log.info( json.dumps( { 'user_id'    : user_id,
                                'message'    : 'Getting list of faces for user_id %s' % ( user_id ) } ) )
        '''

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces2 ).filter( Faces2.user_id == user_id )

        result = [ u.__dict__.copy() for u in query.all() ]
        
        orm.commit()
    
        return result

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Error getting list of user faces: %s' % ( e ) } ) )
        raise

def _get_contact_faces_for_user( user_id, contact_id ):
    '''Returns an array of dictionary objects.  The dictionaries have
    keys with column names from the table, and the relevant values.
    The return value also contains internal keys which are not column
    names.'''

    try:
        '''
        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Getting list of faces for user_id %s, contact_id %s' % ( user_id, contact_id ) } ) )
        '''

        orm = vib.db.orm.get_session()
    
        query = orm.query( Faces2 ).filter( and_( Faces2.user_id == user_id, Faces2.contact_id == contact_id ) )

        result = [ u.__dict__.copy() for u in query.all() ]
        
        orm.commit()
    
        return result

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error getting list of user/contact faces: %s' % ( e ) } ) )
        raise

def _get_face_by_id( face_id ):
    '''Returns either a dictionary like object representing the row
    for in the recognition database for this face, or None if the face
    is not found.'''

    try:
        log.info( json.dumps( { 'message'    : 'Getting face data for face_id: %s' % ( face_id ) } ) )

        orm = vib.db.orm.get_session()
    
        result = orm.query( Faces2 ).filter( Faces2.id == face_id )

        if result.count() == 1:
            face = result[0].__dict__.copy()
            orm.commit()
            return face
        else:
            return None

    except Exception as e:
        log.error( json.dumps( { 'message'    : 'Error getting face data, error was: %s' % ( e ) } ) )
        raise

def _get_face_for_contact_id( user_id, contact_id ):
    '''Returns either a dictionary like object representing the row
    for in the recognition database for a face associated with this
    contact id, or None if no faces are associated with that
    contact_id'''

    try:

        log.info( json.dumps( { 'message'    : 'Getting face data for user_id, contact_id: %s, %s' % ( user_id, contact_id ) } ) )

        orm = vib.db.orm.get_session()
    
        result = orm.query( Faces2 ).filter( and_( Faces2.user_id == user_id, Faces2.contact_id == contact_id ) )

        if result.count() >= 1:
            face = result[0].__dict__.copy()
            orm.commit()
            return face
        else:
            return None

    except Exception as e:
        log.error( json.dumps( { 'message'    : 'Error getting face data, error was: %s' % ( e ) } ) )
        raise

def _get_recognition_stats( user_id=None ):
    '''If user_id is not provided, or is None, return all recognition
    stats.  Otherwise return all stats for that user.'''

    try:
        orm = vib.db.orm.get_session()

        if user_id is not None:
            log.info( json.dumps( { 'user_id' : user_id,
                                    'message' : 'Getting recognition stats for user %s' % ( user_id ) } ) )
            
            stats = orm.query( RecognitionFeedback2 ).filter( RecognitionFeedback2.user_id == user_id )
        else:
            log.info( json.dumps( { 'message' : 'Getting all recognition stats' } ) )
            
            stats = orm.query( RecognitionFeedback2 )

        result = [ s.__dict__.copy() for s in stats.all() ]

        orm.commit()
    
        return result

    except Exception as e:
        log.error( json.dumps( { 'message' : 'Error getting recognition stats: %s' % ( e ) } ) )
        raise        

def _update_recognition_result( recognize_id, result ):
    '''Sets the feedback_received, recognized, and feedback_result
    fields based on result.

    If result is None then feedback_received=True, recognized=False,
    and feedback_result=NULL.
    
    Otherwise, feedback_received=True, recognized=True, and
    feedback_result=result
    '''

    try:
        log.info( json.dumps( { 'message' : 'Updating recognize_id %s with result %s' % ( recognize_id, result ) } ) )

        orm = vib.db.orm.get_session()

        feedback = orm.query( RecognitionFeedback2 ).filter( RecognitionFeedback2.id == recognize_id )[0]

        if result is not None:
            feedback.feedback_received = True
            feedback.recognized = True
            feedback.feedback_result = result
        else:
            feedback.feedback_received = True
            feedback.recognized = False
            feedback.feedback_result = None

        orm.commit()
    
        return

    except Exception as e:
        log.error( json.dumps( { 'message' : 'Error updating recognition feedback row: %s' % ( e ) } ) )
        raise        
