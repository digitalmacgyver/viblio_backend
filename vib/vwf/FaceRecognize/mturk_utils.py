#!/usr/bin/env python

from vib.thirdParty.mturkcore import MechanicalTurk

import vib.vwf.FaceRecognize.merge_tracks_form as merge_tracks_form
import vib.vwf.FaceRecognize.recognize_face_form as recognize_face_form

# DEBUG Get from configuration
MergeHITTypeId = '2PCIA0RYNJ96UXSXBA2MMTUHYKA837'
RecognizeHITTypeId = '2SVYU98JHSTPIHTBQGA9LOBJE7ZDPU'

def create_merge_hit( media_uuid, tracks ):
    '''Hello world hit creation'''
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            # DEBUG add keys to come global configuration
            'aws_key'     : 'AKIAJHD46VMHB2FBEMMA',
            'aws_secret_key' : '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',
            }  )

    create_options = {
        # DEBUG - get this from configuration
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
    '''Hello world hit creation'''
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            # DEBUG add keys to come global configuration
            'aws_key'     : 'AKIAJHD46VMHB2FBEMMA',
            'aws_secret_key' : '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',
            }  )

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

        ret.append( hit_id )

    return ret

def hit_completed( hit_id ):
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            # DEBUG add keys to come global configuration
            'aws_key'     : 'AKIAJHD46VMHB2FBEMMA',
            'aws_secret_key' : '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',
            }  )

    get_options = {
        'HITId' : hit_id 
        }

    result = mt.create_request( 'GetHIT', get_options )

    print "Result was %s" % result
    return result['GetHITResponse']['HIT']['HITStatus'] == 'Reviewable'

def process_merge_hit( hit_id ):
    '''Given a completed hit_id, interpret the results and return a
    merge_tracks, bad_tracks tuple.'''

    return [], []

