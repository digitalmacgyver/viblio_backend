#!/usr/bin/env python

import json
import time
import uuid

from vib.vwf.VWorker import VWorker
from vib.utils import Serialize
from vib.vwf.VPWorkflow import VPW

import vib.vwf.FaceRecognize.mturk_utils as mturk_utils
import vib.vwf.FaceRecognize.db_utils as db_utils

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import logging
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

            log.info( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Working on media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                        } ) )

            log.debug( json.dumps( { 
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Heatbeating"
                        } ) )

            print "heartbeating"
            self.heartbeat()

            if len( tracks ) == 0:
                print "No tracks for media/user_uuid %s/%s, returning." % ( media_uuid, user_uuid )
                print "Returning successfully"
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
                time.sleep( 1.5 * int( VPW[task_name].get( 'default_task_heartbeat_timeout', '300' ) ) )
                # Attempting a heartbeat now results in an exception
                # being thrown.
                raise Exception( "media_uuid: %s, user_uuid %s committed suicide after failing to get lock" % ( media_uuid, user_uuid ) )
            else:
                # We got the lock - proceed
                print "heartbeating"
                self.heartbeat()

            # First we do quality control on the tracks, and merge
            # different tracks into one.
            print "Getting merged tracks"
            merged_tracks, bad_tracks = self._get_merged_tracks( user_uuid, media_uuid, tracks )

            # Then we go through each face post merge and try to
            # recognize them
            print "Recognizing faces"
            recognized_faces, new_faces = self._recognize_faces( user_uuid, media_uuid, merged_tracks )

            print "heartbeating"
            self.heartbeat()

            # Then we persist our results.
            print "Updating contacts"
            result = db_utils.update_contacts( user_uuid, media_uuid, recognized_faces, new_faces, bad_tracks )
            if not result:
                # We had an error updating the DB contacts, most
                # likely there was a race condition and a face we
                # recognized no longer exists due to user behavior in
                # the UI.  Retry the entire task from scratch.
                return { 'ACTIVITY_ERROR' : True, 'retry' : True }
            else:
                print "Returning successfully"
                return { 'media_uuid' : media_uuid, 'user_uuid' : user_uuid }
            
        except Exception as e:
            # We had an unknown error, still try to retry but allow
            # the heartbeat timeout to bring us back.
            print "Exception was: %s" % ( e )
            raise
        finally:
            # On the way out let go of our lock if we've got it.
            if self.lock_acquired:
                self.faces_lock.release()

    def _get_merged_tracks( self, user_uuid, media_uuid, tracks ):
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

        print "heartbeating"
        self.heartbeat()

        # DEBUG - Sort the incoming tracks with face recognition.

        print "Creating merge hit"
        hit_id = mturk_utils.create_merge_hit( media_uuid, tracks )
        print "Had HITId of %s" % hit_id

        print "heartbeating"
        self.heartbeat()

        hit_completed = False
        
        while not mturk_utils.hit_completed( hit_id ):
            print "Hit not complete, sleeping for %d seconds" % self.polling_secs
            time.sleep( self.polling_secs )
            print "heartbeating"
            self.heartbeat()

        answer_dict = mturk_utils.get_answer_dict_for_hit( hit_id )

        merged_tracks, bad_tracks = self._process_merge( answer_dict, tracks )

        print "heartbeating"
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
                raise Exception( "Found answer for track %d which was not present in tracks: %s" % track_id, tracks )
            
            if label.startswith( 'answer_' ):
                disposition = value.rpartition( '_' )[2]

                if disposition == 'new':
                    print "Found new track %d" % track_id
                    if track_id not in merge_dict:
                        merge_dict[track_id] = [ track_disposition[track_id]['track'] ]
                    else:
                        merge_dict[track_id].append( track_disposition[track_id]['track'] )

                elif disposition == 'notface':
                    print "Bad notface track %d" % track_id
                    bad_tracks.append( track_disposition[track_id]['track'] )

                elif disposition == 'twoface':
                    print "Bad twoface track %d" % track_id
                    bad_tracks.append( track_disposition[track_id]['track'] )

            elif label.startswith( 'merge_' ):
                if value:
                    print "Merging track %d with %s" % ( track_id, value )
                    merge_target = int( value )

                    if merge_target not in track_disposition:
                        raise Exception( "Asked to merge track %d with nonexistent track %d, tracks was: %s" % track_id, merge_target, tracks )

                    if merge_target not in merge_dict:
                        merge_dict[merge_target] = [ track_disposition[track_id]['track'] ]
                    else:
                        merge_dict[merge_target].append( track_disposition[track_id]['track'] )

            else:
                raise Exception( "Unexpected answer label %s" % label )
            
        merged_tracks = []

        for track_id in sorted( merge_dict.keys() ):
            merged_tracks.append( merge_dict[track_id] )

        return merged_tracks, bad_tracks

    def _recognize_faces( self, user_uuid, media_uuid, merged_tracks ):
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

        print "heartbeating"
        self.heartbeat()

        contacts = db_utils.get_picture_contacts_for_user_uuid( user_uuid )

        print "heartbeating"
        self.heartbeat()

        if len( contacts ) > 0:
            # There user has at least one contact with a picture

            # DEBUG - actually do some work with recognition here.
            guess = None
            if len( contacts ) > 1: 
                guess = contacts[0]
                contacts = contacts[1:]

            print "Creating recognize hit"
            # hit_tracks is An array of hash elements with HITId and
            # merged_tracks keys.
            hit_tracks = mturk_utils.create_recognize_hits( media_uuid, merged_tracks, contacts, guess )
            print "Created %d hits" % len( hit_tracks )

            print "heartbeating"
            self.heartbeat()

            answer_dicts = {}

            hit_completed = False
        
            for hit_track in hit_tracks:
                hit_id = hit_track['HITId']
                while not mturk_utils.hit_completed( hit_id ):
                    print "Hit not complete, sleeping for %d seconds" % self.polling_secs
                    time.sleep( self.polling_secs )
                    print "heartbeating"
                    self.heartbeat()
                answer_dicts[hit_id] = mturk_utils.get_answer_dict_for_hit( hit_id )
                print "heartbeating"
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
            
        print "heartbeating"
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
        recognized_faces = {}
        new_faces = {}

        for hit_track in hit_tracks:
            hit_id = hit_track['HITId']
            person_tracks = hit_track['merged_tracks']

            print "Working on HIT %s" % hit_id

            answer_dict = answer_dicts[ hit_id ]

            value = answer_dict['QuestionFormAnswers']['Answer']['FreeText']

            print "Found value %s" % ( value )

            if value == 'new_face':
                contact_uuid = str( uuid.uuid4() )
                new_faces[contact_uuid] = person_tracks
            elif value.startswith( 'recognized_' ):
                contact_uuid = value.rpartition( '_' )[2]
                recognized_faces[contact_uuid] = person_tracks
            else:
                raise Exception( "Unexpected answer value %s" % value )
                
        return recognized_faces, new_faces

def _get_sample_data():
    return {
        #"media_uuid": "12a66e50-3497-11e3-85db-d3cef39baf91",
        "media_uuid": "12a66e50-3497-11e3-85db-d3cef39bb004",
            "tracks": [
                {
                    "faces": [
                        {
                            "Genderconfidence": 34,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_0_2.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "2470109b93cc87d8d52c18c39cc6a20b",
                            "GlassesConfidence": 40,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 9,
                            "DarkGlassesConfidence": 12,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 66.6208,
                            "face_id": 1,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 26,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 38,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_0_3.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "2a7297129393d0a70f08cc4ab672d745",
                            "GlassesConfidence": 85,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 255,
                            "DarkGlassesConfidence": 61,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 62.3178,
                            "face_id": 2,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 12,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 33,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_0_4.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "796b65e2fdec46ab6eb716d38a5dd10a",
                            "GlassesConfidence": 40,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 10,
                            "DarkGlassesConfidence": 26,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 65.8241,
                            "face_id": 3,
                            "Blink": "yes",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 47,
                            "Glasses": "No"
                            }
                        ],
                    "visiblity_info": [
                        {
                            "end_frame": 5666,
                            "start_frame": 633
                            },
                        {
                            "end_frame": 8366,
                            "start_frame": 5733
                            }
                        ],
                    "track_id": 0
                    },
                {
                    "faces": [
                        {
                            "Genderconfidence": 255,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_1_1.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "e0b4d4acbf962226fb78b94dcc6ec0de",
                            "GlassesConfidence": 36,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 31,
                            "DarkGlassesConfidence": 255,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 59.0595,
                            "face_id": 0,
                            "Blink": "yes",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 100,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 25,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_1_2.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "91535fe780fb30e1a7ee71df3922d885",
                            "GlassesConfidence": 75,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 54,
                            "DarkGlassesConfidence": 35,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 76.1929,
                            "face_id": 1,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 100,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 50,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_1_3.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "3ddc10d58070ead9639de9cc486b6ba4",
                            "GlassesConfidence": 80,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 81,
                            "DarkGlassesConfidence": 46,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 71.3377,
                            "face_id": 2,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 56,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 48,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_1_4.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "34e05fed65ed8ea7db592d78aa43529e",
                            "GlassesConfidence": 70,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 67,
                            "DarkGlassesConfidence": 30,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 67.2394,
                            "face_id": 3,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 83,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 74,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_1_5.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "06a38b5f10954e68d345a66de8b4057c",
                            "GlassesConfidence": 70,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 72,
                            "DarkGlassesConfidence": 23,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 68.1247,
                            "face_id": 4,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 85,
                            "Glasses": "No"
                            }
                        ],
                    "visiblity_info": [
                        {
                            "end_frame": 15533,
                            "start_frame": 833
                            },
                        {
                            "end_frame": 37066,
                            "start_frame": 36433
                            },
                        {
                            "end_frame": 48600,
                            "start_frame": 20000
                            },
                        {
                            "end_frame": 48733,
                            "start_frame": 48666
                            },
                        {
                            "end_frame": 61600,
                            "start_frame": 40533
                            },
                        {
                            "end_frame": 64933,
                            "start_frame": 62000
                            },
                        {
                            "end_frame": 65100,
                            "start_frame": 65000
                            },
                        {
                            "end_frame": 66933,
                            "start_frame": 65333
                            },
                        {
                            "end_frame": 73866,
                            "start_frame": 73500
                            },
                        {
                            "end_frame": 74100,
                            "start_frame": 74000
                            },
                        {
                            "end_frame": 75500,
                            "start_frame": 75333
                            },
                        {
                            "end_frame": 76500,
                            "start_frame": 75666
                            },
                        {
                            "end_frame": 76700,
                            "start_frame": 76666
                            }
                        ],
                    "track_id": 1
                    },
                {
                    "faces": [
                        {
                            "Genderconfidence": 20,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_2_1.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "c87428eda6e41e4760a1517b8402731c",
                            "GlassesConfidence": 43,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 66,
                            "DarkGlassesConfidence": 46,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 62.4248,
                            "face_id": 0,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 90,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 62,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_2_2.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "6ad0dab4710e89335f902ca739d6af35",
                            "GlassesConfidence": 53,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 66,
                            "DarkGlassesConfidence": 23,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 65.7695,
                            "face_id": 1,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 45,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 255,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_2_3.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "9ccb02d540f10c67141a55644c660242",
                            "GlassesConfidence": 43,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 62,
                            "DarkGlassesConfidence": 48,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 60.3161,
                            "face_id": 2,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 71,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 255,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_2_4.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "029ffe1ead992e0d8bb0eaae94253b8d",
                            "GlassesConfidence": 52,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 39,
                            "DarkGlassesConfidence": 27,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 66.6435,
                            "face_id": 3,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 88,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 53,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_2_5.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "a6a2b37a7371bec479a361a3ec27c5e9",
                            "GlassesConfidence": 48,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 79,
                            "DarkGlassesConfidence": 35,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 68.2131,
                            "face_id": 4,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 100,
                            "Glasses": "No"
                            }
                        ],
                    "visiblity_info": [
                        {
                            "end_frame": 34266,
                            "start_frame": 19433
                            },
                        {
                            "end_frame": 37600,
                            "start_frame": 26033
                            },
                        {
                            "end_frame": 92566,
                            "start_frame": 37833
                            },
                        {
                            "end_frame": 94000,
                            "start_frame": 92600
                            },
                        {
                            "end_frame": 100366,
                            "start_frame": 94266
                            }
                        ],
                    "track_id": 2
                    },
                {
                    "faces": [
                        {
                            "Genderconfidence": 255,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_3_1.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "451581b56c136ded16b73fa52c165845",
                            "GlassesConfidence": 48,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 30,
                            "DarkGlassesConfidence": 255,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 59.6994,
                            "face_id": 0,
                            "Blink": "yes",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 61,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 43,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_3_2.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "d46150e213c82235339c9444799d59cb",
                            "GlassesConfidence": 46,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 7,
                            "DarkGlassesConfidence": 29,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 66.2533,
                            "face_id": 1,
                            "Blink": "yes",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 88,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 32,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_3_3.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "bf47c110aff46390e31641f5cc623a80",
                            "GlassesConfidence": 59,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 77,
                            "DarkGlassesConfidence": 19,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 66.9296,
                            "face_id": 2,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 65,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 42,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_3_4.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "b38f4182c2fdbe8e9a50ab335e0cdb87",
                            "GlassesConfidence": 55,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 70,
                            "DarkGlassesConfidence": 44,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 65.6005,
                            "face_id": 3,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 82,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 255,
                            "width": 65,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_3_5.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "ece97a5dfb3562bd72118e9cafbe04d2",
                            "GlassesConfidence": 60,
                            "height": 65,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 90,
                            "DarkGlassesConfidence": 27,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 69.3573,
                            "face_id": 4,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 95,
                            "Glasses": "No"
                            }
                        ],
                    "visiblity_info": [
                        {
                            "end_frame": 95733,
                            "start_frame": 83933
                            },
                        {
                            "end_frame": 96733,
                            "start_frame": 96600
                            }
                        ],
                    "track_id": 3
                    },
                {
                    "faces": [
                        {
                            "Genderconfidence": 21,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_4_2.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "94c946a9e6a387401cdf30ef57f681e2",
                            "GlassesConfidence": 21,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 26,
                            "DarkGlassesConfidence": 9,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 53.7607,
                            "face_id": 1,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 9,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 40,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_4_3.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "0da080c8095dc64224a72cfa9e351aa0",
                            "GlassesConfidence": 26,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 16,
                            "DarkGlassesConfidence": 59,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 57.9286,
                            "face_id": 2,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 24,
                            "Glasses": "No"
                            },
                        {
                            "Genderconfidence": 255,
                            "width": 64,
                            "s3_key": "12a66e50-3497-11e3-85db-d3cef39baf91/12a66e50-3497-11e3-85db-d3cef39baf91_face_4_4.jpg",
                            "face_rotation_yaw": 0,
                            "s3_bucket": "viblio-uploaded-files",
                            "md5sum": "5696d510136b19f9d86eb961ed97c0de",
                            "GlassesConfidence": 80,
                            "height": 64,
                            "face_rotation_pitch": 0,
                            "DarkGlasses": "No",
                            "Blinkconfidence": 17,
                            "DarkGlassesConfidence": 45,
                            "Gender": "female",
                            "face_rotation_roll": 0,
                            "face_confidence": 53.6297,
                            "face_id": 3,
                            "Blink": "no",
                            "MouthOpen": "Yes",
                            "MouthOpenConfidence": 85,
                            "Glasses": "No"
                            }
                        ],
                    "visiblity_info": [
                        {
                            "end_frame": 100366,
                            "start_frame": 94033
                            }
                        ],
                    "track_id": 4
                    }
                ],
            "user_uuid": "C209A678-03AF-11E3-8D79-41BD85EDDE05"
            }
