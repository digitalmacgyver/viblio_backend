import json
import logging
import re
import requests

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

default_namespace = config.rekog_namespace

def crawl_faces_for_user( user_uuid, fb_access_token, fb_user_id, fb_friends, namespace=None ):
    '''For a given Facebook ID and a list of friends with { id, name }
    elements, execute the crawl faces ReKognition task.

    Returns a list of the result(s) of the request(s) made in JSON
    format.
    '''

    if namespace == None:
        namespace = default_namespace

    results = []

    # DEBUG
    print "Working in namespace %s: " % namespace

    # Compose the list of faces to crawl, no more than 20 at a time.
    max_friends_per_call = 19
    for idx in range( 0, max( len( fb_friends ), 1 ), max_friends_per_call ):
        jobs = ''
        if idx == 0:
            jobs = 'face_crawl_[' + fb_user_id + ';'
        else:
            jobs = 'face_crawl_['
    
        first_friend = True
        for friend in fb_friends[idx:idx+max_friends_per_call]:
            if first_friend:
                first_friend = False
            else:
                jobs += ';'

            jobs += friend['id']

        jobs += ']'

        print "Job was %s" % jobs

        data = {
            'api_key'      : rekog_api_key,
            'api_secret'   : rekog_api_secret,
            'jobs'         : jobs,
            'fb_id'        : fb_user_id,
            'access_token' : fb_access_token,
            'name_space'   : namespace,
            'user_id'      : user_uuid
            }

        r = requests.post( "http://rekognition.com/func/api/", data )
        results.append( r.json() )

    return results

def train_for_user( user_uuid, namespace = None ):
    '''Call the Rekognition training API for all faces for the
    user.

    Returns the request result in JSON format.'''

    if namespace == None:
        namespace = default_namespace

    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_train',
        'name_space'   : namespace,
        'user_id'      : user_uuid
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

def visualize_for_user( user_uuid, num_img_return_pertag=1, namespace = None ):
    '''Calls the ReKognition Visualize function and returns an array
    of { tag, url, index : [#, #, ...] } elements for each tagged
    person.

    Defaults to only one image per person.'''

    if namespace == None:
        namespace = default_namespace

    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_visualize',
        'num_img_return_pertag' : num_img_return_pertag,
        'name_space'   : namespace,
        'user_id'      : user_uuid
        }

    r = requests.post( "http://rekognition.com/func/api/", data )

    return r.json()['visualization']

def rename_tag_for_user( user_uuid, old_tag, new_tag, namespace=None ):
    '''Renames all occurences of old_tag to new_tag for the user.
    Returns the result of the API call in JSON format.'''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_rename',
        'tag'          : old_tag,
        'new_tag'      : new_tag,
        'name_space'   : namespace,
        'user_id'      : user_uuid
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

