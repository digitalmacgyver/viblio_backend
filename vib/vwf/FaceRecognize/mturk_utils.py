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
    '''Creates a mechanical turn task for the quality control and
    de-duplication of the input tracks.'''

    create_options = {
        'HITTypeId' : MergeHITTypeId,
        'LifetimeInSeconds' : 36*60*60,
        'RequesterAnnotation' : media_uuid,
        'UniqueRequestToken' : 'merge-' + media_uuid,
        'Question' : merge_tracks_form.get_question( tracks )
        }

    print "Creating Merge Track HIT for %s" % media_uuid
    result = mt.create_request( 'CreateHIT', create_options )

    hit_id = None
    try:
        hit_id = result['CreateHITResponse']['HIT']['HITId']
    except:
        try:
            # Handle the case where this hit already exists.
            hit_id = result['CreateHITResponse']['HIT']['Request']['Errors']['Error']['Data'][1]['Value']
        except Exception as e:
            print "Could not determine hit_id, error: %s" % e
            raise

    return hit_id

def create_recognize_hits( media_uuid, merged_tracks, contacts, guess, recognize_id ):
    '''Returns an array of hash with keys:
    merged_tracks : the tracks associated with the HIT for this element
    HITId : the hit_id for this element
    '''
    ret = []

    for person_tracks in merged_tracks:
        # We need a deterministic ID here across multiple runs of the
        # script / submissions of input to ensure we don't re-create
        # HITs that have already been created.
        id_for_person_track = min( a['track_id'] for a in person_tracks )

        create_options = {
            'HITTypeId' : RecognizeHITTypeId,
            'LifetimeInSeconds' : 36*60*60,
            'RequesterAnnotation' : media_uuid + '-%d' % ( id_for_person_track ),
            'UniqueRequestToken' : ( 'recognize-%d-' % ( id_for_person_track ) ) + media_uuid,
            'Question' : recognize_face_form.get_question( person_tracks, contacts, guess, recognize_id )
            }

        print "Creating Recognize Face HIT for media/track %s/%s" % ( media_uuid, id_for_person_track )
        result = mt.create_request( 'CreateHIT', create_options )

        hit_id = None
        try:
            hit_id = result['CreateHITResponse']['HIT']['HITId']
        except:
            try:
                # Handle the case where this hit already exists.
                hit_id = result['CreateHITResponse']['HIT']['Request']['Errors']['Error']['Data'][1]['Value']
            except Exception as e:
                print "Could not determine hit_id, error: %s" % e
                raise

        ret.append( { 'HITId' : hit_id, 'merged_tracks' : person_tracks } )

    return ret

def hit_completed( hit_id ):
    result = get_hit( hit_id )

    print "Getting status for hit: %s" % hit_id
    status = mt.get_response_element( 'HITStatus', result )

    if status == None:
        raise Exception( "Could not determine status for hit: %s" % hit_id )
    else:
        return status == 'Reviewable'

def get_hit( hit_id ):
    get_options = {
        'HITId' : hit_id 
        }

    print "Getting hit: %s" % hit_id
    result = mt.create_request( 'GetHIT', get_options )

    return result

def get_assignment_for_hit( hit_id ):
    '''Note: This method assumes there is only one assignment for the
    HIT. Within the scope of the FaceRecognize application this is
    true.'''
    get_assignments_options = {
        'HITId' : hit_id 
        }

    print "Getting assignment for hit: %s" % hit_id
    result = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )

    return result

def get_answer_dict_for_hit( hit_id ):
    assignment = get_assignment_for_hit( hit_id )
    answer = mt.get_response_element( 'Answer', assignment )
    answer_dict = xmltodict.parse( answer )

    return answer_dict

