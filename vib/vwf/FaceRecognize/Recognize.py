#!/usr/bin/env python

import json
import logging
import time
import uuid

from vib.utils import Serialize
from vib.vwf.VPWorkflow import VPW
from vib.vwf.VWorker import VWorker

import vib.vwf.FaceRecognize.mturk_utils as mturk_utils
import vib.vwf.FaceRecognize.db_utils as db_utils

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
            # How often should we poll Mechanical Turk to see if a job
            # is done.
            self.polling_secs = 10
            
            self.lock_acquired = False

            user_uuid  = options['FaceDetect']['user_uuid']
            media_uuid = options['FaceDetect']['media_uuid']
            tracks     = options['FaceDetect']['tracks']

            self.user_uuid = user_uuid
            self.media_uuid = media_uuid

            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Working on media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                        } ) )

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Heartbeating"
                        } ) )
            self.heartbeat()

            if tracks == None or len( tracks ) == 0:
                log.info( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "No tracks for media/user_uuid %s/%s, returning." % ( media_uuid, user_uuid )
                            } ) )
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

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Attempting to acquire serialization lock for %s" % user_uuid
                        } ) )

            # This will wait for up to 2 minutes trying to get the
            # lock.
            self.lock_acquired = self.faces_lock.acquire()

            if not self.lock_acquired:
                # We didn't get the lock - we want this task to be
                # terminated, and we want another task the chance to
                # get in and use it's slot in our limited number of
                # workers who can handle these jobs.
                #
                # We achieve this by sleeping until the timeout for
                # this task would have expired, and then exiting.
                time.sleep( 1.5 * int( VPW[self.task_name].get( 'default_task_heartbeat_timeout', '300' ) ) )
                # Attempting a heartbeat now results in an exception
                # being thrown.
                message = "media_uuid: %s, user_uuid %s committed suicide after failing to get lock" % ( media_uuid, user_uuid )
                log.info( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : message
                            } ) )

                raise Exception( message )
            else:
                # We got the lock - proceed
                log.debug( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Heartbeating"
                            } ) )
                self.heartbeat()

            # First we do quality control on the tracks, and merge
            # different tracks into one.
            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Getting merged tracks"
                        } ) )
            merged_tracks, bad_tracks = self._get_merged_tracks( tracks )

            # Then we go through each face post merge and try to
            # recognize them
            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Recognizing faces"
                        } ) )
            recognized_faces, new_faces = self._recognize_faces( merged_tracks )

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Heartbeating"
                        } ) )
            self.heartbeat()

            # Then we persist our results.
            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Updating contacts"
                        } ) )
            result = db_utils.update_contacts( user_uuid, media_uuid, recognized_faces, new_faces, bad_tracks )
            if not result:
                # We had an error updating the DB contacts, most
                # likely there was a race condition and a face we
                # recognized no longer exists due to user behavior in
                # the UI.  Retry the entire task from scratch.
                return { 'ACTIVITY_ERROR' : True, 'retry' : True }
            else:
                log.info( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Returning successfully"
                            } ) )
                return { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid }
            
        except Exception as e:
            # We had an unknown error, fail the job - it will be
            # retried if we're under max_failures.
            log.error( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Exception was: %s" % ( e )
                        } ) )
            raise
        finally:
            # On the way out let go of our lock if we've got it.
            if self.lock_acquired:
                self.faces_lock.release()

    def _get_merged_tracks( self, tracks ):
        '''
        Input - the user and media_uuids we are working with, and an
        array of tracks, each of which includes an array of faces.
        Each Face has a URI for where it is in S3.
        
        This method:
        1) Heartbeats Amazon SWF that it is working.
        2) Creates a Mechanical Turk task.
        3) Polls Mechanical Turk until that task is done.
        4) Interprets the Mechanical Turk results.

        Returns two arrays:
        merged_tracks, bad_tracks

        The elements of merged_tracks are themselves arrays, each
        element being a track that was merged with the others in the
        same element.

        The elements of bad_tracks are dictionaries, with keys
        "reason" and "track" and values describing the reason this
        track was bad, and the track itself that was bad.
        '''

        user_uuid = self.user_uuid
        media_uuid = self.media_uuid

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        # DEBUG - Sort the incoming tracks with face recognition.

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Creating merge hit"
                    } ) )
        hit_id = mturk_utils.create_merge_hit( media_uuid, tracks )
        log.info( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'hit_id' : hit_id,
                    'message' : "Created merge hit with HITId of %s" % hit_id
                    } ) )

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        hit_completed = False
        
        while not mturk_utils.hit_completed( hit_id ):
            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'hit_id' : hit_id,
                        'message' : "Hit %s not complete, sleeping for %d seconds" % ( hit_id, self.polling_secs )
                    } ) )

            time.sleep( self.polling_secs )

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Heartbeating"
                        } ) )
            self.heartbeat()

        answer_dict = mturk_utils.get_answer_dict_for_hit( hit_id )

        merged_tracks, bad_tracks = self._process_merge( answer_dict, tracks )

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        return merged_tracks, bad_tracks

    def _process_merge( self, answer_dict, tracks ):
        '''Given a set of user answers, interpret the results and
        return a merge_tracks, bad_tracks tuple.

        Answers are in ['QuestionFormAnswers']['Answer']
          * Label is ['QuestionIdentifier']
          * Value is ['FreeText']
        
        Merge answers take the form:
        answer_track# - Will be one of:
        * track#_notface
        * track#_twoface
        * track#_new
        
        merge_track_track# - Will always be present, with a (hopefully)
        # numeric value in our range of tracks, or None
        '''
        
        user_uuid = self.user_uuid
        media_uuid = self.media_uuid

        track_disposition = {}
        merge_dict = {}
        bad_tracks = []

        for track in tracks:
            track_id = track['track_id']
            track_disposition[track_id] = { 'track' : track }
        
        # Amazon's answer XML is a bit goofy - they give singleton
        # elements instead of an array with one item.
        answer_list = answer_dict['QuestionFormAnswers']['Answer']
        if not isinstance( answer_list, list):
            answer_list = [ answer_list ]

        for answer in answer_list:
            label = answer['QuestionIdentifier']
            value = answer['FreeText']

            track_id = int( label.rpartition( '_' )[2] )
            if track_id not in track_disposition:
                message = "Found answer for track %d which was not present in tracks: %s" % ( track_id, tracks )
                log.error( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'track_id' : track_id,
                            'message' : message
                            } ) )
                raise Exception( message )
            
            if label.startswith( 'answer_' ):
                disposition = value.rpartition( '_' )[2]

                if disposition == 'new':
                    log.info( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'track_id' : track_id,
                                'message' : "Found new track %d" % track_id
                                } ) )
                    if track_id not in merge_dict:
                        merge_dict[track_id] = [ track_disposition[track_id]['track'] ]
                    else:
                        merge_dict[track_id].append( track_disposition[track_id]['track'] )

                elif disposition == 'notface':
                    log.warning( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'track_id' : track_id,
                                'error_code' : 'not_face',
                                'message' : "Bad not face track %d" % track_id
                                } ) )
                    bad_tracks.append( track_disposition[track_id]['track'] )

                elif disposition == 'twoface':
                    log.warning( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'track_id' : track_id,
                                'error_code' : 'two_face',
                                'message' : "Bad two face track %d" % track_id
                                } ) )
                    bad_tracks.append( track_disposition[track_id]['track'] )

            elif label.startswith( 'merge_' ):
                if value:
                    log.info( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'track_id' : track_id,
                                'value' : value,
                                'message' : "Merging track %d with %s" % ( track_id, value )
                                } ) )
                    merge_target = int( value )

                    if merge_target not in track_disposition:
                        message = "Asked to merge track %d with nonexistent track %d, tracks was: %s" % ( track_id, merge_target, tracks )
                        log.error( json.dumps( { 
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'track_id' : track_id,
                                    'merge_target' : merge_target,
                                    'message' : message
                                    } ) )
                        raise Exception( message )

                    if merge_target not in merge_dict:
                        merge_dict[merge_target] = [ track_disposition[track_id]['track'] ]
                    else:
                        merge_dict[merge_target].append( track_disposition[track_id]['track'] )

            else:
                message = "Unexpected answer label %s" % label
                log.error( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : message
                            } ) )
                raise Exception( message )
            
        merged_tracks = []

        for track_id in sorted( merge_dict.keys() ):
            merged_tracks.append( merge_dict[track_id] )

        return merged_tracks, bad_tracks

    def _recognize_faces( self, merged_tracks ):
        '''
        Input: The media_uuid and user_uuid that we are working on,
        and an array of merged tracks.  Each element of merged tracks
        is itself an array of track data structures.

        This method:
        1) Heartbeats Amazon SWF that it is working.
        2) Creates one Mechanical Turk task for each element of merged_tracks.
        3) Polls Mechanical Turk until all the Mechanical Turk tasks are done.
        4) Interprets the Mechanical Turk results.

        Returns two dictionaries:
        recognized_faces, new_faces

        The keys of both dictionaries are uuids, in the case of
        recognized_faces they are the contact_uuids of the recognized
        faces.

        The values in both dictionaries are arrays of track data
        structures which were determined to be for those faces.
        '''

        user_uuid = self.user_uuid
        media_uuid = self.media_uuid

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        contacts = db_utils.get_picture_contacts_for_user_uuid( user_uuid )

        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        if len( contacts ) > 0:
            # There user has at least one contact with a picture

            # DEBUG - actually do some work with recognition here.
            guess = None
            if len( contacts ) > 1: 
                guess = contacts[0]
                contacts = contacts[1:]

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Creating %d recognition hits" % len( merged_tracks )
                        } ) )

            # hit_tracks is An array of hash elements with HITId and
            # merged_tracks keys.
            hit_tracks = mturk_utils.create_recognize_hits( media_uuid, merged_tracks, contacts, guess )
            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Created %d hits, HITIds are: %s" % ( len( hit_tracks ), hit_tracks )
                        } ) )

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Heartbeating"
                        } ) )
            self.heartbeat()

            answer_dicts = {}

            hit_completed = False
        
            for hit_track in hit_tracks:
                hit_id = hit_track['HITId']
                while not mturk_utils.hit_completed( hit_id ):
                    log.info( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'hit_id' : hit_id,
                                'message' : "Hit %s not complete, sleeping for %d seconds" % ( hit_id, self.polling_secs )
                                } ) )

                    time.sleep( self.polling_secs )
                    self.heartbeat()
                answer_dicts[hit_id] = mturk_utils.get_answer_dict_for_hit( hit_id )

                log.debug( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Heartbeating"
                            } ) )
                self.heartbeat()

            recognized_faces, new_faces = self._process_recognized( answer_dicts, hit_tracks, guess )
        else:
            # The user has no contacts with pictures, so everyone here is new.

            # DEBUG - Consider doing recognition here with Facebook
            # stuff - we'd have to seed images from Facebook in for
            # our reviewers?
            recognized_faces = {}
            new_faces = {}
            for track in hit_tracks:
                person_tracks = hit_track['merged_tracks']
                contact_uuid = str( uuid.uuid4() )
                new_faces[contact_uuid] = person_tracks
            
        log.debug( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Heartbeating"
                    } ) )
        self.heartbeat()

        return recognized_faces, new_faces

    def _process_recognized( self, answer_dicts, hit_tracks, guess ):
        '''Given sets of user answers, interpret the results to tag
        users.  Return a recognized_faces, new_faces tuple.

        Answers are in ['QuestionFormAnswers']['Answer']
          * Label is ['QuestionIdentifier']
          * Value is ['FreeText']
        
        Merge answers take the form:
        answer - Will be one of:
        * recognized_[uuid]
        * new_face
        '''

        user_uuid = self.user_uuid
        media_uuid = self.media_uuid

        recognized_faces = {}
        new_faces = {}

        for hit_track in hit_tracks:
            hit_id = hit_track['HITId']
            person_tracks = hit_track['merged_tracks']

            answer_dict = answer_dicts[ hit_id ]

            value = answer_dict['QuestionFormAnswers']['Answer']['FreeText']

            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'hit_id' : hit_id,
                        'value' : value,
                        'message' : "Found value %s for hit %s" % ( value, hit_id )
                        } ) )

            if value == 'new_face':
                contact_uuid = str( uuid.uuid4() )
                new_faces[contact_uuid] = person_tracks
            elif value.startswith( 'recognized_' ):
                contact_uuid = value.rpartition( '_' )[2]
                recognized_faces[contact_uuid] = person_tracks
            else:
                message = "Unexpected answer value %s" % value
                log.error( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : message
                            } ) )
                raise Exception( message )
                
        return recognized_faces, new_faces

