#!/usr/bin/env python

import xmltodict

from vib.thirdParty.mturkcore import MechanicalTurk

import vib.vwf.FaceRecognize.merge_tracks_form as merge_tracks_form
import vib.vwf.FaceRecognize.recognize_face_form as recognize_face_form

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

MergeHITTypeId = config.MergeHITTypeId
RecognizeHITTypeId = config.RecognizeHITTypeId

mt = MechanicalTurk( 
    { 
        'use_sandbox'           : True, 
        'stdout_log'            : True, 
        'aws_key'     : config.awsAccess,
        'aws_secret_key' : config.awsSecret
        }  )

def create_merge_hit( media_uuid, tracks ):
    '''Hello world hit creation'''

    create_options = {
        'HITTypeId' : MergeHITTypeId,
        'LifetimeInSeconds' : 36*60*60,
        'RequesterAnnotation' : media_uuid,
        'UniqueRequestToken' : 'merge-' + media_uuid,
        'Question' : merge_tracks_form.get_question( tracks )
        }

    result = mt.create_request( 'CreateHIT', create_options )
    print "Result was %s" % result

    # DEBUG - Think about what happens if there is some other sort of
    # error.
    hit_id = None
    try:
        hit_id = result['CreateHITResponse']['HIT']['HITId']
    except:
        # Handle the case where this hit already exists.
        hit_id = result['CreateHITResponse']['HIT']['Request']['Errors']['Error']['Data'][1]['Value']

    return hit_id

def create_recognize_hits( media_uuid, merged_tracks, contacts, guess ):
    '''Returns an array of hash with keys:
    merged_tracks : the tracks associated with the HIT for this element
    HITId : the hit_id for this element
    '''
    ret = []

    for person_tracks in merged_tracks:
        id_for_person_track = min( a['track_id'] for a in person_tracks )
        create_options = {
            # DEBUG - get this from configuration
            'HITTypeId' : RecognizeHITTypeId,
            'LifetimeInSeconds' : 36*60*60,
            'RequesterAnnotation' : media_uuid + '-%d' % ( id_for_person_track ),
            'UniqueRequestToken' : ( 'recognize-%d-' % ( id_for_person_track ) ) + media_uuid,
            'Question' : recognize_face_form.get_question( person_tracks, contacts, guess )
            }

        result = mt.create_request( 'CreateHIT', create_options )
        print "Result was %s" % result
        hit_id = None
        try:
            hit_id = result['CreateHITResponse']['HIT']['HITId']
        except:
            # Handle the case where this hit already exists.
            hit_id = result['CreateHITResponse']['HIT']['Request']['Errors']['Error']['Data'][1]['Value']

        ret.append( { 'HITId' : hit_id, 'merged_tracks' : person_tracks } )

    return ret

def hit_completed( hit_id ):
    result = get_hit( hit_id )

    return mt.get_response_element( 'HITStatus', result ) == 'Reviewable'

def get_hit( hit_id ):
    get_options = {
        'HITId' : hit_id 
        }

    result = mt.create_request( 'GetHIT', get_options )

    print "Result was %s" % result
    return result

def get_assignment_for_hit( hit_id ):
    get_assignments_options = {
        'HITId' : hit_id 
        }
    
    result = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )
    # DEBUG - Check that there is only one assignment.
    print "Result was %s" % result
    return result

def get_answer_dict_for_hit( hit_id ):
    assignment = get_assignment_for_hit( hit_id )
    answer = mt.get_response_element( 'Answer', assignment )
    answer_dict = xmltodict.parse( answer )

    return answer_dict

#for answer in answer_dict['QuestionFormAnswers']['Answer']:
#    label = answer['QuestionIdentifier']
#    value = answer['FreeText']

# NOTE: We'll get back merge_track_n for everything except track 0,
# just with a value of None if it wasn't selected.  Typical output:
# merge_track_1 : None
# merge_track_2 : None
# merge_track_3 : 1
# merge_track_4 : 2
# answer_0 : 0_new
# answer_1 : 1_new
# answer_2 : 2_new
