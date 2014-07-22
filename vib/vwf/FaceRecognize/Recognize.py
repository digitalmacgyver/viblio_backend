#!/usr/bin/env python

import json
import logging
import time
import uuid

import vib.cv.FaceRecognition.api as rec
from vib.utils import Serialize
import vib.rekog.utils
from vib.vwf.VPWorkflow import VPW
from vib.vwf.VWorker import VWorker

import vib.vwf.FaceRecognize.db_utils as db_utils
import vib.utils.s3 as s3

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

class Recognize( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'FaceRecognize'
    
    def run_task( self, options ):
        '''Perform the face recognition logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''

        try:
            # If the detection_confidence is less than this we set the
            # face as bad face.
            self.detection_threshold = 0.8
            
            # If the recognition_confidence is greater than this we
            # set the face as machine recognized.
            self.recognition_threshold = 0.8
            
            self.lock_acquired = False

            user_uuid  = options['user_uuid']
            media_uuid = options['media_uuid']
            recognition_input = options['FaceDetect'].get( 'recognition_input', None )

            if recognition_input is None:
                log.info( json.dumps( {  'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "No tracks for media/user_uuid %s/%s, returning." % ( media_uuid, user_uuid ) } ) )
                db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
                
                return { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid }
            else:
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : 'Recognition input is at bucket: %s, key: %s' % ( recognition_input['s3_bucket'], recognition_input['s3_key'] ) } ) )
            
            input_bucket = recognition_input['s3_bucket']
            input_key = recognition_input['s3_key']

            tracks = json.loads( s3.download_string( input_bucket, input_key ) )['tracks']

            self.user_uuid = user_uuid
            self.media_uuid = media_uuid

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "Working on media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )

            if tracks == None or len( tracks ) == 0:
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "No tracks for media/user_uuid %s/%s, returning." % ( media_uuid, user_uuid ) } ) )
                
                db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
                
                return { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid }

            # Ensure we're the only one working on this particular
            # user.  This allows us to correctly spot and track a
            # person who is present in 2 videos that are uploaded
            # simultaneously.
            self.faces_lock = Serialize.Serialize( app = 'FaceRecognize',
                                                   # These assignments
                                                   # are not a typo.
                                                   object_name = user_uuid,
                                                   owner_id = media_uuid,
                                                   app_config = config,
                                                   heartbeat = 30,
                                                   timeout = 120 )

            log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Attempting to acquire serialization lock for %s" % user_uuid } ) )

            # This will wait for up to 2 minutes trying to get the
            # lock.
            self.lock_acquired = self.faces_lock.acquire()

            if not self.lock_acquired:
                # We didn't get the lock - we want this task to be
                # terminated, and we want another task the chance to
                # get in and use its slot in our limited number of
                # workers who can handle these jobs.
                #
                # We achieve this by sleeping until the timeout for
                # this task would have expired, and then exiting.
                self.stop_heartbeat()
                time.sleep( 1.5 * int( VPW[self.task_name].get( 'default_task_heartbeat_timeout', '300' ) ) )
                # Attempting a heartbeat now results in an exception
                # being thrown.
                message = "media_uuid: %s, user_uuid %s committed suicide after failing to get lock" % ( media_uuid, user_uuid )
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : message } ) )
                raise Exception( message )

            # Tracks data structure is like:
            # { "tracks" : [ { 
            #                  "track_id" : 0,
            #                  "faces" : [ {
            #                               "s3_bucket" : ...,
            #                               "s3_key" : ..., }, ],
            #                 }, ]
            #   "user_uuid" : ...,
            #   "media_uuid" : ... }
            for track in tracks:
                if 'faces' in track:
                    for track_face in track['faces']:
                        self._handle_face( track['track_id'], track_face, user_uuid, media_uuid )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "Returning successfully" } ) )
            
            db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
                
            return { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid }
            
        except Exception as e:
            # We had an unknown error, fail the job - it will be
            # retried if we're under max_failures.
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Exception was: %s" % ( e ) } ) )
            raise
        finally:
            # On the way out let go of our lock if we've got it.
            if self.lock_acquired:
                self.faces_lock.release()

    def _handle_face( self, track_id, track_face, user_uuid, media_uuid ):
        '''For each face, send it to Orbues for detection:
        * If not a face, add it to the DB as a not_face
        * If confidence < 0.8 add it to the DB as bad_face
        * Else attempt recognition:
        *  If recognition > 0.8 add to DB as machine_recognized
        *  else add as new_face
        '''
        try:
            url = "%s%s" % ( config.ImageServer, track_face['s3_key'] )
            detection = vib.rekog.utils.detect_face( url )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "Processing face at: %s" % ( url ) } ) )

            result = 'not_face'

            user_id = db_utils.get_user_id( user_uuid )

            detection_confidence = None
            recognition_confidence = None

            if 'face_detection' not in detection:
                result = 'not_face'
            elif len( detection['face_detection'] ) < 1:
                result = 'not_face'
            else:
                recog_face = detection['face_detection'][0]
                detection_confidence = recog_face['confidence']
                
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "Detection confidence was: %f" % ( detection_confidence ) } ) )
                
                if detection_confidence < self.detection_threshold:
                    result = 'bad_face'
                else:
                    matches = rec.recognize_face( user_id, url )
                    if matches is None:
                        result = 'new_face'
                    elif len( matches['faces'] ) == 0:
                        result = 'new_face'
                    else:
                        recognition_confidence = matches['faces'][0]['recognition_confidence']
                            
                        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                                'user_uuid' : user_uuid,
                                                'message' : "Matched contact %d with confidence %f" % ( matches['faces'][0]['contact_id'], recognition_confidence ) } ) )
                        
                        if recognition_confidence >= self.recognition_threshold:
                            result = 'machine_recognized'
                            rec.recognition_feedback( matches['recognize_id'], 1 )
                        else:
                            result = 'new_face'
                            rec.recognition_feedback( matches['recognize_id'], None )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "RESULT WAS: %s" % ( result ) } ) )

            if result in [ 'bad_face', 'two_face', 'not_face' ]:
                # Update DB record with appropriate data.
                db_utils.update_face( user_uuid, media_uuid, track_id, track_face, result, None, None )
            elif result == 'machine_recognized':
                # Add to DB with contact ID of ['contact_id']
                # Add to recog with that tag.
                #
                # First verify that the contact we recognized against still exists in our Viblio system.
                if db_utils.contact_exists( matches['faces'][0]['contact_id'] ):
                    face_id = db_utils.update_face( user_uuid, media_uuid, track_id, track_face, result, recognition_confidence, matches['faces'][0]['contact_id'] )
                    rec.add_faces( user_id, matches['faces'][0]['contact_id'], [ { 'user_id'     : user_id,
                                                                                   'contact_id'  : matches['faces'][0]['contact_id'],
                                                                                   'face_id'     : face_id,
                                                                                   'face_url'    : url,
                                                                                   'external_id' : None } ] )

                    # We want to fix up the photo of this user in a
                    # special set of circumstances:
                    #  * If this is the only video this user appears in.
                    #  * The current profile picture of this contact is from facebook.
                    #
                    # Then we update the photo to be one of the ones
                    # from this video.  Otherwise we don't change it.
                    db_utils.update_contact_picture_uri( user_uuid, media_uuid, matches['faces'][0]['contact_id'], picture_uri=track_face['s3_key'] )

                else:
                    # We were recognized against a non-existint
                    # contact - perhaps one that has been deleted.
                    # 
                    # Delete the bad information from recognition.
                    log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                               'user_uuid' : user_uuid,
                                               'message' : "Matched non-existant contact: %s - removing that contact from Recognition." % ( matches['faces'][0]['contact_id'] ) } ) )
                    rec.delete_contact( user_id, matches['faces'][0]['contact_id'] )
                    result = 'new_face'
                                        
            if result == 'new_face':
                # Add to DB as new face
                # Add to recog with new contact_id
                ( face_id, contact_id ) = db_utils.add_face( user_uuid, media_uuid, track_id, track_face, result, recognition_confidence )
                rec.add_faces( user_id, contact_id, [ { 'user_id'     : user_id,
                                                        'contact_id'  : contact_id,
                                                        'face_id'     : face_id,
                                                        'face_url'    : url,
                                                        'external_id' : None } ] )
        except Exception as e:
            raise
        

