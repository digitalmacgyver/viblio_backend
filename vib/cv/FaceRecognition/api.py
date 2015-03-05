import json
import logging
import uuid

# The caller of this script should define a logger that is
# vib.cv.FaceRecognition so this logger inherits those properties.
log = logging.getLogger( __name__ )

import vib.rekog.utils as rekog
import vib.cv.FaceRecognition.db_utils as recog_db
import vib.cv.FaceRecognition.helpers as helpers
from vib.utils import Serialize

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
# face_id - integer identifying the particular image for the contact
# in the external system.
#
# face_url - a URL to an image of the face
#
# external_id - This key must be provided, it's value can be None or
# an optional arbitrary integer the external system can set to further
# identify this face in the external system (if user_id, contact_id,
# and face_id are not sufficient)
#
# The return value for each function will be a hash with the following
# keys:
#
# added, deleted, unchanged, error
#
# Reflecting the disposition of each face from the input.

def add_faces( user_id, contact_id, faces ):
    '''For an array of faces, adds them to the recognition system.

    Input faces are dictionary like objects with:
    user_id, contact_id, face_id - integers which form a unique key for this face
    face_url - a URL where the image for this face can be accessed
    external_id - arbitrary integer for use by the calling application

    Faces which already exist (as determined by the presence of the
    same user_id, contact_id, face_id) will be denoted in the
    unchanged return value.
    
    Not all faces will be added, if a face can not be detected, or the
    face properties are not amenible to recognition due to quality or
    pose, this face will be returned in the unchanged return value.

    In the return value faces for which the recognition system did not
    detect exactly one face in the face image will be returned in the
    unchanged result, other unexpected errors will be returned in
    errors.
    '''

    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'add_faces:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True
                                    
        added = []
        unchanged = []
        error = []

        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Adding faces for user_id %s, contact_id %s.' % ( user_id, contact_id ) } ) )

        face_keys = [ 'user_id', 'contact_id', 'face_id', 'face_url', 'external_id' ]

        for face in faces:
            try:
                valid_face = True
                for key in face_keys:
                    if key not in face:
                        valid_face = False
                        break
                if not valid_face:
                    raise Exception( "Face did not have all required fields %s" % face_keys )

                if face['user_id'] != user_id:
                    raise Exception( "Error, face for user_id %s had user_id of %s " % ( user_id, face['user_id'] ) )

                if face['contact_id'] != contact_id:
                    raise Exception( "Error, face for contact_id %s had contact_id of %s " % ( contact_id, face['contact_id'] ) )

                log.debug( json.dumps( { 'user_id'    : user_id,
                                         'contact_id' : contact_id,
                                         'message'    : "Working on face %s" % ( helpers._format_face( face ) ) } ) )

                #try:
                #    CHECK_VALUE = recog_db._check_face_exists( face['user_id'], face['contact_id'], face['face_id'] )
                #except Exception as e:
                #    log.error( json.dumps( { 'user_id'    : user_id,
                #                             'contact_id' : contact_id,
                #                             'message'    : "_CHECK_FACE_EXISTS FAILED: %s" % ( e ) } ) )
                #    sys.exit(0)

                #if CHECK_VALUE:
                if recog_db._check_face_exists( face['user_id'], face['contact_id'], face['face_id'] ):
                    log.debug( json.dumps( { 'user_id'    : user_id,
                                             'contact_id' : contact_id,
                                             'message'    : "Face already exists in database." } ) )
                    
                    unchanged.append( face )
                else:
                    idx = rekog.add_face_for_user( user_id, face['face_url'], contact_id, config.recog_v2_namespace, strict=True )
                    #try:
                    #    idx = rekog.add_face_for_user( user_id, face['face_url'], contact_id, config.recog_v2_namespace, strict=True )
                    #except Exception as e:
                    #    log.error( json.dumps( { 'user_id'    : user_id,
                    #                             'contact_id' : contact_id,
                    #                             'message'    : "ADD_FACE_FOR_USER FAILED: %s" % ( e ) } ) )
                    #    sys.exit(0)
                
                    if idx is not None:
                        log.debug( json.dumps( { 'user_id'    : user_id,
                                                 'contact_id' : contact_id,
                                                 'message'    : "Face added to recognition with idx: %s" % ( idx ) } ) )

                        face['idx'] = idx
                        
                        recog_db._add_face( user_id, contact_id, face )

                        #try:
                        #    recog_db._add_face( user_id, contact_id, face )
                        #except Exception as e:
                        #    log.error( json.dumps( { 'user_id'    : user_id,
                        #                             'contact_id' : contact_id,
                        #                             'message'    : "_ADD_FACE FAILED: %s" % ( e ) } ) )
                        #    sys.exit(0)

                        log.debug( json.dumps( { 'user_id'    : user_id,
                                                 'contact_id' : contact_id,
                                                 'message'    : "Added face to database." } ) )

                        added.append( face )
                    else:
                        log.debug( json.dumps( { 'user_id'    : user_id,
                                                 'contact_id' : contact_id,
                                                 'message'    : "No face found by Recognition, skipping." } ) )
                        unchanged.append( face )

            except Exception as e:
                log.error( json.dumps( { 'user_id'    : user_id,
                                         'contact_id' : contact_id,
                                         'message'    : 'Error while adding face: %s' % ( e ) } ) )
                error.append( face )

        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'About to reconcile faces for %s, %s' % ( user_id, contact_id ) } ) )

        if not helpers._reconcile_db_rekog( user_id, contact_id ):
            result = rekog.train_for_user_contact( user_id, contact_id, config.recog_v2_namespace )
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'contact_id' : contact_id,
                                     'rekog_result' : result,
                                     'message'    : 'Trained Recognition for user_id %s' % ( user_id ) } ) )

        return { 
            'added'     : added,
            'deleted'   : [],
            'unchanged' : unchanged,
            'error'     : error
            }

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error while adding faces: %s' % ( e ) } ) )
        raise
    finally:
        if lock_acquired:
            lock.release()

def delete_contact( user_id, contact_id ):
    '''Deletes all information in the Recognition system about the
    given contact_id, if any.'''

    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'delete_contact:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True

        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Deleting contact %s for user %s.' % ( contact_id, user_id ) } ) )
        
        faces = recog_db._get_contact_faces_for_user( user_id, contact_id )

        # Try to delete faces for this contact in ReKognition,
        # regardless of whether they showed up in the DB.
        result = rekog.delete_face_for_user( user_id, str( contact_id ), None, config.recog_v2_namespace )
        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'rekog_result' : result,
                                 'message'    : 'Deleted faces for user %s, contact_id %s' % ( user_id, contact_id ) } ) )

        if len( faces ):
            # This means there were DB faces to delete, retrain
            # ReKognition.  Note that we don't unconditionally retrain
            # because that is an expensive API call.
            recog_db._delete_contact_faces_for_user( user_id, contact_id )
            result = rekog.train_for_user_contact( user_id, contact_id, config.recog_v2_namespace )
            log.debug( json.dumps( { 'user_id'      : user_id,
                                     'contact_id'   : contact_id,
                                     'rekog_result' : result,
                                     'message'      : 'Trained ReKognition user %s' % ( user_id ) } ) )

        helpers._reconcile_db_rekog( user_id, contact_id )

        return { 
            'added'     : [],
            'deleted'   : faces,
            'unchanged' : [],
            'error'     : []
            }

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error while deleting contact: %s' % ( e ) } ) )
        raise
    finally:
        if lock_acquired:
            lock.release()

def delete_faces( user_id, contact_id, faces ):
    '''Given a user_id, contact_id, and array of faces, delete the
    faces data structures present in the array.

    The faces array can contain either:

    * Face data structures returned by the methods of this api, or
    * Dictionary like objects with an id field
    '''

    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'delete_faces:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True

        log.info( json.dumps( { 'user_id'    : user_id,
                                'contact_id' : contact_id,
                                'message'    : 'Deleting faces related to contact %s for user %s.' % ( contact_id, user_id ) } ) )

        deleted = []
        ( faces, unchanged, error ) = helpers._populate_faces( user_id, contact_id, faces )

        delete_indices = ''

        for face in faces:
            # Build up list of faces to delete.
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'contact_id' : contact_id,
                                     'message'    : 'Adding index %s to list of faces to delete in ReKognition for %s.' % ( face['idx'], user_id ) } ) )

            delete_indices += ';%s' % ( face['idx'] )

        if len( delete_indices ):
            delete_indices = delete_indices[1:]
            try:
                result = rekog.delete_face_for_user( user_id, str( contact_id ), delete_indices, config.recog_v2_namespace )
                log.debug( json.dumps( { 'user_id'    : user_id,
                                         'contact_id' : contact_id,
                                         'rekog_result' : result,
                                         'message'    : 'Deleted faces %s for user %s, contact_id %s' % ( delete_indices, user_id, contact_id ) } ) )
            except Exception as e:
                log.error( json.dumps( { 'user_id'    : user_id,
                                         'contact_id' : contact_id,
                                         'message'    : 'Error deleting face for contact %s for user %s, error was: %s' % ( contact_id, user_id, e ) } ) )
                raise

        # Remove the deleted faces from our tracking database.
        recog_db._delete_faces( faces )

        # Our deletes and past errors from other executions may have
        # led to our database being out of sync with ReKognition, if
        # so reconcile the two.
        #
        # If _reconcile returns true it means it did a training call
        # so we don't need to explicitly train ourselves.
        if not helpers._reconcile_db_rekog( user_id, contact_id ):
            result = rekog.train_for_user_contact( user_id, contact_id, config.recog_v2_namespace )
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'contact_id' : contact_id,
                                     'rekog_result' : result,
                                     'message'    : 'Trained Recognition for user_id %s' % ( user_id ) } ) )

        return { 
            'added'     : [],
            'deleted'   : deleted,
            'unchanged' : unchanged,
            'error'     : error
            }

    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error while deleting faces: %s' % ( e ) } ) )
        raise
    finally:
        if lock_acquired:
            lock.release()

def delete_user( user_id ):
    '''Delete a user, and all associated contacts, entirely.'''

    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'delete_user:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True

        log.info( json.dumps( { 'user_id'    : user_id,
                                'message'    : 'Deleting user_id: %s' % ( user_id ) } ) )

        deleted = recog_db._get_all_faces_for_user( user_id )

        # Delete the user from ReKognition
        result = None
        try:
            result = rekog.delete_user( user_id, config.recog_v2_namespace )
        except Exception as e:
            log.warning( json.dumps( { 'user_id'    : user_id,
                                       'message' : "WARNING: Exception thrown deleting face from ReKognition - most likely this face does not exist in that system. Exception was: %s" % ( e ) } ) )
            
        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'rekog_result' : result,
                                 'message'    : 'Deleted all recognition data for user_id %s' % ( user_id ) } ) )

        # Delete faces from database
        recog_db._delete_all_user_faces( user_id )

        return { 
            'added'     : [],
            'deleted'   : deleted,
            'unchanged' : [],
            'error'     : []
            }
    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Error while deleting user: %s' % ( e ) } ) )
        raise
    finally:
        if lock_acquired:
            lock.release()

def get_faces( user_id, contact_id = None ):
    '''Returns an array face data structures associated with this
    user_id and contact_id.

    If contact_id is not provided, or is None, returns faces for all
    contacts associated with this user.

    Returns None if an unexpected error occurs.
    '''

    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'get_faces:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True

        helpers._reconcile_db_rekog( user_id, contact_id )
        
        if contact_id is not None:
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'contact_id' : contact_id,
                                     'message'    : 'Getting faces for user_id %s, contact_id %s' % ( user_id, contact_id ) } ) )
            return recog_db._get_contact_faces_for_user( user_id, contact_id )
        else:
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'message'    : 'Getting all faces for user_id %s' % ( user_id ) } ) )
            return recog_db._get_all_faces_for_user( user_id )

    except Exception as e:
        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'contact_id' : contact_id,
                                 'message'    : 'Error while getting faces for user_id %s, contact_id %s: %s' % ( user_id, contact_id, e ) } ) )
        return None
    finally:
        if lock_acquired:
            lock.release()

def recognize_face( user_id, face_url ):
    '''Takes in a face_url and tries to recognize whether that face is
    one of the known contact_ids of this user.

    If no face is detected at face_url, or if an unexpected error
    occurs, None is returned.

    Otherwise, an array with 0-3 augmented faces is returned, in
    descending order of match confidence.  Each such face corresponds
    to a distinct contact_id and has an additional
    'recognition_confidence' key which is a floating point value from
    0-1, where higher values indicate more confidence. 

    Since there can be many faces associated with a given contact id,
    the particular face returned is non-deterministic, it is one of
    the faces associated with that contact_id.  The match confidence
    refers to the confidence the recognized face is that contact_id.
    '''
    
    lock_acquired = False
    lock = None

    try:
        # Ensure this is the only FaceRecognition task going on for
        # this user for the duration of this call.
        lock = Serialize.Serialize( app = 'Recognition',
                                    object_name = str( user_id ),
                                    owner_id = 'recognize_face:'+str( uuid.uuid4() ),
                                    app_config = config,
                                    heartbeat = 10,
                                    timeout = 30 )
        lock.acquire()
        lock_acquired = True

        log.info( json.dumps( { 'user_id'    : user_id,
                                'message'    : 'Recognizing face for user_id: %s from: %s' % ( user_id, face_url ) } ) )

        matches = rekog.recognize_for_user( user_id, face_url, config.recog_v2_namespace )

        reconciled_contacts = {}

        if matches is None:
            log.debug( json.dumps( { 'user_id'    : user_id,
                                     'message'    : 'No recognition matches found.' } ) )
            return None
        else:
            faces = []
            for match in matches:
                try:
                    contact_id = int( match['tag'] )
                except Exception as e:
                    # Either there was no 'tag' in match, or the tag wasn't an int.
                    if 'tag' in match:
                        log.error( json.dumps( { 'user_id'    : user_id,
                                                 'message'    : 'Invalid tag found, tag must be integer, skipping. Match was: %s' % ( match ) } ) )
                        log.info( json.dumps( { 'user_id'    : user_id,
                                                'message'    : 'Deleting faces with invalid tag: %s for user_id: %s' % ( match['tag'], user_id ) } ) )
                        rekog.delete_face_for_user( user_id, match['tag'], namespace=config.recog_v2_namespace )
                    else:
                        log.error( json.dumps( { 'user_id'    : user_id,
                                                 'message'    : 'Invalid match returned from ReKognition, skipping, match was: %s' % ( match ) } ) )

                    # Move on to the next face.
                    continue
                    
                recognition_confidence = float( match['score'] )
                log.debug( json.dumps( { 'user_id'    : user_id,
                                         'message'    : 'Recognition confidence was: %s' % ( recognition_confidence ) } ) )
                if contact_id not in reconciled_contacts:
                    helpers._reconcile_db_rekog( user_id, contact_id )
                    reconciled_contacts[contact_id] = True
                face = recog_db._get_face_for_contact_id( user_id, contact_id )
                if face is not None:
                    face['recognition_confidence'] = recognition_confidence
                    faces.append( face )
                    if len( faces ) == 3:
                        break

        result = {}
        result['faces'] = sorted( faces, key=lambda x: -x['recognition_confidence'] )[:3]

        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Adding recognition feedback.' } ) )
        result['recognize_id'] = recog_db._add_recognition_feedback( user_id, face_url, result['faces'] )

        log.debug( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Found %s candidate matches.' % ( len( result ) ) } ) )

        return result
    except Exception as e:
        log.error( json.dumps( { 'user_id'    : user_id,
                                 'message'    : 'Error while recognizing face for user_id %s: %s' % ( user_id, e ) } ) )
        return None
    finally:
        if lock_acquired:
            lock.release()

def recognition_feedback( recognize_id, result ):
    '''recognize_id is the value returned by a prior call to recognize_face

    result is either:
        None if none of the faces from recognize_face were matches
        1, 2, or 3 if the 1st, 2nd, or 3rd face from recognize_face was a match (in the case where multiple faces were matches the lowest matching number should be used)
    '''

    try:
        recog_db._update_recognition_result( recognize_id, result )
        return
    except Exception as e:
        log.error( json.dumps( { 'recognize_id' : recognize_id,
                                 'message'      : 'Error storing recognizing face feedback: %s' % ( e ) } ) )
        raise

def recognition_stats( user_id=None ):
    '''If user_id is not provided or is None, stats for the entire
    system are returned, otherwise stats only for that user_id are
    returned.

    Return value is:

    {  'recognize_calls' : 743, # The total number of recognize_face calls 
                                # for which any candidate matches were returned
       'feedback_calls'  : 367, # The number of recognize_face calls for which 
                                # recognition_feedback has been provided
       'true_positives'  : 312, # The number of successful matches made
       'false_positives' :  55, # The number of times no match was found }

    Note that false_positives + true_positives == feedback_falls
    '''

    try:
        stats = recog_db._get_recognition_stats( user_id )

        recognize_calls = 0
        feedback_calls  = 0
        true_positives  = 0
        false_positives = 0

        for stat in stats:
            recognize_calls += 1
            if stat['feedback_received']:
                feedback_calls += 1
                if stat['recognized']:
                    true_positives += 1
                else:
                    false_positives += 1

        return {
            'recognize_calls' : recognize_calls,
            'feedback_calls'  : feedback_calls,
            'true_positives'  : true_positives,
            'false_positives' : false_positives
            }
    except Exception as e:
        log.error( json.dumps( { 'recognize_id'    : user_id,
                                 'message'    : 'Error getting recognizing face statistics for user_id %s: %s' % ( user_id, e ) } ) )
        raise

def recognition_stat_details( user_id=None ):
    '''If user_id is not provided or is None, stats for the entire
    system are returned, otherwise stats only for that user_id are
    returned.

    Returns an array of dictionary like objects with many fields,
    including:

    {  'id'                : 12,   # The recognition_id of this row returned from recognize_face
    'user_id'           : 443,
    'face_url'          : 'http://...', 
    'face1_id'          : 69, 
    'face1_confidence'  : 0.98,
    'face2_id'          : 69, 
    'face2_confidence'  : 0.98,
    'face3_id'          : None, 
    'face3_confidence'  : None,
    'feedback_received' : True, # Has feedback about this match been received?
    'recognized'        : True,
    'feedback_result'   : 2,    # The value of recognize_feedback's result
    }
    '''

    try:
        return recog_db._get_recognition_stats( user_id )
    except Exception as e:
        log.error( json.dumps( { 'recognize_id'    : user_id,
                                 'message'    : 'Error getting recognizing face statistic details for user_id %s: %s' % ( user_id, e ) } ) )
        raise
