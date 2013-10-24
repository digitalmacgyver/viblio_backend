#!/usr/bin/env python

import json
import uuid

from vib.vwf.VWorker import VWorker

# NEXT UP
#
# 1. Get _process_hit working:
# Hello world hit.
# Hello world hit with image from our site.
# Same by submit, accept, poll, resolve, post next
# Fix layout.

class FaceRecognize( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'FaceRecognize'
    
    def run_task( self, options ):
        '''Perform the face recognition logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''
        
        # DEBUG - placeholder till we get real data on input.
        options = _get_sample_data()

        user_contacts = _get_contacts_for_user( user_uuid )

        recognized_faces = 0
        total_faces = 0

        matched_contacts = {}
        new_contacts = {}

        for track in options['tracks']:
            track_id = track['track_id']
            faces = track['faces']
            
            guess_uuid = _get_recognition_guess( faces )['contact_uuid']
            guess_contact = _get_contact_by_uuid( guess_uuid )
            
            result = _process_hit( faces, user_contacts, guess_contact, new_contacts )
            
            answer = result['answer']
            matched_uuid = result['contact_uuid']

            if answer == 'not_face':
                _log_error( "Not a face", options, track_id )
            elif answer == 'different_faces':
                _log_error( "Different people in same track", options, track_id )
            elif answer == 'recognized_face':
                recognized_faces += 1
                total_faces +=1
                matched_contacts[track_id] = matched_uuid
                _train_face( matched_uuid, faces )
            elif answer == 'existing_face':
                total_faces += 1
                matched_contacts[track_id] = matched_uuid
                _train_face( matched_uuid, faces )
            elif answer == 'new_face':
                total_faces += 1
                new_uuid = str( uuid.uuid4() )
                new_contacts[track_id] = { 
                    'uuid' : new_uuid,
                    's3_bucket' : faces[0]['s3_bucket'],
                    's3_key' : faces[0]['s3_key']
                    }
                _train_face( new_uuid, faces )

        if not _update_database( user_contacts, matched_contacts, new_contacts, tracks ):
            return { 
                'ACTIVITY_ERROR' : True, 
                'retry' : True 
                }
        else:
            return { 
                'media_uuid' : options['media_uuid'],
                'user_uuid' : options['user_uuid'],
                }

def _update_database( user_contacts, matched_contacts, new_contacts, media_uuid, user_uuid, tracks ):
    '''DEBUG In another library, rationalize everything, return false
    if a contact has changed'''
    return


def _train_face( recognizer_id, faces ):
    '''DEBUG - TBD in another library'''
    return

def _process_hit( faces, user_contacts, guess_contact ):
    '''DEBUG - TBD'''
    return

def _log_error( message, options, track_id ):
    '''DEBUG - Notify someone that our tracking is doing bad stuff.'''
    return


# DEBUG test data for stub methods below.
test_contacts = {
    'e4f4a8f4-e6de-4b46-887f-56b604883751' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-3e95a54a-afa4-479b-9893-f5307c71a7df.jpg', 'intellivision_id' : -99.9 },

    '7bdcb12f-8a4b-4970-919f-300dc45f8e6e' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-01e6ca90-95e2-47c3-a33d-22fa2dd1b413.jpg', 'intellivision_id' : -99.9 },
    '350c353d-96ea-4d2c-a601-8951fdd790e6' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-f800b9c8-1f1e-4778-a016-6389200212fb.jpg', 'intellivision_id' : -99.9 },
    'cb6b60d5-cfc2-42c0-877f-e948bdbf654f' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-a09ed5db-976b-44b8-bda1-5b0c8f7db2ba.jpg', 'intellivision_id' : -99.9 },
    'ce926853-5621-4a4e-86b2-4758824ba311' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-5578fa1c-c948-4f5f-89f1-58ff94ddca33.jpg', 'intellivision_id' : -99.9 },
    '42339711-c033-491a-983b-1ce81ecf010e' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-cfddfcf3-0eda-4966-ab5b-933ebcd913a0.jpg', 'intellivision_id' : -99.9 },
    'cbe49436-8e7e-47de-8cd9-adb8215020de' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-8d4181d1-bf60-49b7-b0f9-935fae935098.jpg', 'intellivision_id' : -99.9 },
    '0c04b683-fe79-4ab6-93bb-39ac9f096649' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-fb82b100-9990-43ab-8803-67946397fd0d.jpg', 'intellivision_id' : -99.9 },
    '4c037dd9-0843-4460-830d-a45b77aaf2f5' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-5e65755c-3e6f-47fc-9781-92dc9bb18461.jpg', 'intellivision_id' : -99.9 },
    'dd468776-56c4-4892-8a88-a9651ddbd5a9' : { 'picture_uri' : '4dd58749-958c-4fd2-93b6-0e49403c01af/face-587edda1-7acf-4e7a-a67c-17134adcdf61.jpg', 'intellivision_id' : -99.9 }
    }


def _get_contacts_for_user( uuid ):
    '''DEBUG - will be implemented as a seperate method in a DB
    accessing library'''
    
    return test_contacts

def _get_contact_by_uuid( uuid ):
    '''DEBUG - will be implemented as a seperate method in a DB
    accessing library'''

    return test_contacts[ uuid ]

def _get_recognition_guess( faces ):
    '''DEBUG - to be implemented after we get the basic MTurk stuff
    working

    DEBUG - To be implemented in it's own method/class in
    vib/recognize or something.
    '''

    return { 
        'contact_uuid' : 'e4f4a8f4-e6de-4b46-887f-56b604883751',
        }

def _get_sample_data():
    return json.loads( {
            "media_uuid": "12a66e50-3497-11e3-85db-d3cef39baf91",
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
            } )
