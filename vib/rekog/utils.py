import json
import logging
import re
import requests

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

default_namespace = config.rekog_namespace

def add_face_for_user( user_id, url, tag=None, namespace=None ):
    '''Adds face at URL for specified user.  If tag is specified the
    name is added with that tag.

    Returns either the index of the face in Rekognition (a string), or
    None in the case that:
    a. ReKognition found no faces
    b. ReKognition found more than one face
    c. There was an error
    '''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_add',
        'name_space'   : namespace,
        'user_id'      : user_id,
        'tag'          : tag, 
        'img_index'    : face_idx
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    
    result = r.json()

    if result['usage']['status'] != 'Succeed.':
        return None
    elif len( result['face_detection'] ) != 1:
        return None
    else:
        return result['face_detection'][0]['img_index']

def crawl_faces_for_user( user_id, fb_access_token, fb_user_id, fb_friends, namespace=None, skip_self=False ):
    '''For a given Facebook ID and a list of friends with { id, name }
    elements, execute the crawl faces ReKognition task.

    Returns a list of the result(s) of the request(s) made in JSON
    format.
    '''

    if namespace == None:
        namespace = default_namespace

    results = []

    # Compose the list of faces to crawl, no more than 20 at a time.
    max_friends_per_call = 19
    for idx in range( 0, max( len( fb_friends ), 1 ), max_friends_per_call ):
        jobs = ''
        if idx == 0 and not skip_self:
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
            'user_id'      : user_id
            }

        r = requests.post( "http://rekognition.com/func/api/", data )
        results.append( r.json() )

    return results

def train_for_user( user_id, namespace = None ):
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
        'user_id'      : user_id
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

def visualize_for_user( user_id, num_img_return_pertag=1, no_image=False, show_default=False, namespace = None ):
    '''Calls the ReKognition Visualize function and returns an array
    of { tag, url, index : ['1', '2', ...] } elements for each tagged
    person.

    Defaults to only one image per person.

    If num_img_return_pertag is None the default Rekoginition behavior
    (all tags) is done.

    If no_image is True then no images are generated, only the text
    response is generated.

    If show_detault is True then untagged images are included under
    the _x_all tag.'''

    if namespace == None:
        namespace = default_namespace

    jobs = 'face_visualize'
    if no_image:
        jobs += '_no_image'
    if show_default:
        jobs += '_show_default_tag'

    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : jobs,
        'name_space'   : namespace,
        'user_id'      : user_id
        }

    if num_img_return_pertag is not None:
        data['num_img_return_pertag'] = num_img_return_pertag

    r = requests.post( "http://rekognition.com/func/api/", data )

    return r.json()['visualization']

def rename_tag_for_user( user_id, old_tag, new_tag, namespace=None ):
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
        'user_id'      : user_id
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

def delete_face_for_user( user_id, tag, face_idx, namespace=None ):
    '''Deletes the face tagged with index face_idx for user_id in
    namespace.  The special _x_all tag can be used for untagged faces.

    Optionally face_idx can be formatted as '1;2;3' to delete multiple
    faces at once'''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_delete',
        'name_space'   : namespace,
        'user_id'      : user_id,
        'tag'          : tag, 
        'img_index'    : face_idx
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

def delete_user( user_id, namespace=None ):
    '''Deletes the entirety of the ReKognition system for the provider
    user, namespace'''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_delete',
        'name_space'   : namespace,
        'user_id'      : user_id
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

def cluster_for_user( user_id, namespace=None ):
    '''Clusters the user in question and returns the result.  Result
    format is:

    { 'clusters' : [ { 'tag': 'cluster0', 'img_index': [1,2,3] }, ... ],
      'usage'    : { 'status' : 'Succeed.', ... } }
    '''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_cluster',
        'name_space'   : namespace,
        'user_id'      : user_id
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()
