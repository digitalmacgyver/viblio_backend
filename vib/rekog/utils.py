import base64
import json
import logging
import re
import requests

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

default_namespace = config.rekog_namespace

def add_face_for_user( user_id, url, tag=None, namespace=None, strict=False, min_confidence=0.8, max_yaw=45, max_pitch=45 ):
    '''Adds face at URL for specified user.  If tag is specified the
    name is added with that tag.

    Returns either the index of the face in ReKognition (a string), or
    None in the case that:
    a. ReKognition found no faces
    c. There was an error

    If strict is True then we also reject faces and return None if:
    * Recognition confidence score is less than confidence_threshold
    * Absolut value of yaw or pitch is more than max_yaw or max_pitch
    '''

    if namespace == None:
        namespace = default_namespace
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_add_beauty',
        'name_space'   : namespace,
        'user_id'      : user_id,
        'tag'          : tag,
        'urls'         : url
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    
    result = r.json()

    if result['usage']['status'] != 'Succeed.':
        return None
    elif len( result['face_detection'] ) == 1:
        if not strict:
            return result['face_detection'][0]['img_index']
        else:
            bad_face = False
            if result['face_detection'][0]['confidence'] < min_confidence:
                bad_face = True
            if abs( result['face_detection'][0]['pose']['yaw'] ) > max_yaw:
                bad_face = True
            if abs( result['face_detection'][0]['pose']['pitch'] ) > max_pitch:
                bad_face = True
                
            if bad_face:
                delete_face_for_user( user_id, '_x_all', result['face_detection'][0]['img_index'], namespace )
                return None
            else:
                return result['face_detection'][0]['img_index']
    elif len( result['face_detection'] ) > 1:
        # Sometimes ReKognition detects multiple faces when there is
        # only one face.  Keep only the best face.
        best = None
        best_confidence = 0
        delete = []
        for face in result['face_detection']:
            face_confidence = face['confidence']
            if face_confidence > best_confidence:
                if best is not None:
                    delete.append( best )
                best_confidence = face_confidence
                best = face
            else:
                delete.append( face )

        for face in delete:
            delete_face_for_user( user_id, '_x_all', face['img_index'], namespace )

        if not strict:
            return best['img_index']
        else:
            bad_face = False
            if best['confidence'] < min_confidence:
                bad_face = True
            if abs( best['pose']['yaw'] ) > max_yaw:
                bad_face = True
            if abs( best['pose']['pitch'] ) > max_pitch:
                bad_face = True
                
            if bad_face:
                delete_face_for_user( user_id, '_x_all', best['img_index'], namespace )
                return None
            else:
                return best['img_index']
    else:
        return None

def cluster_for_user( user_id, namespace=None ):
    '''Clusters the user in question and returns the result.  Result
    format is:

    { 'clusters' : [ { 'tag': 'cluster0', 'img_index': [1,2,3] }, ... ],
      'usage'    : { 'status' : 'Succeed.', ... } }

    Raises an exception if the API call does not succeed.
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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result
    else:
        raise Exception( result['usage']['status'] )

def crawl_faces_for_user( user_id, fb_access_token, fb_user_id, fb_friends, namespace=None, skip_self=False ):
    '''For a given Facebook ID and a list of friends with { id, name }
    elements, execute the crawl faces ReKognition task.

    Returns a list of the result(s) of the request(s) made in JSON
    format.  Any API failures are included in the results.
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

def delete_face_for_user( user_id, tag, face_idx, namespace=None ):
    '''Deletes the face tagged with index face_idx for user_id in
    namespace.  The special _x_all tag can be used for untagged faces.

    Optionally face_idx can be formatted as '1;2;3' to delete multiple
    faces at once

    Raises an exception if the API call does not succeed.'''

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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result
    else:
        raise Exception( result['usage']['status'] )

def delete_user( user_id, namespace=None ):
    '''Deletes the entirety of the ReKognition structure for the
    provided user, namespace

    Raises an exception if the API call does not succeed.'''

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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result
    else:
        raise Exception( result['usage']['status'] )

def recognize_for_user( user_id, url, namespace = None ):
    '''Call the ReKognition recognize API for the URL within the
    user_id/namespace.

    Returns None if there is no face at URL.

    If multiple faces are detected in the input URL, matches for the
    face with the highest confidence are returned.
    
    Returns an array of up up to 3 matches in descending order of
    recognition confidence of this format:
    [ { 'tag' : 'matched_image_tag', 'score' : '0.03' }, ... ]
    '''

    if namespace == None:
        namespace = default_namespace

    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_recognize',
        'name_space'   : namespace,
        'user_id'      : user_id,
        'urls'         : url
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    result = r.json()

    print "RECOGNITION RESULT: %s" % ( result )


    if result['usage']['status'] != 'Succeed.':
        return None
    elif ( len( result['face_detection'] ) == 1 ) and ( 'matches' in result['face_detection'][0] ):
        return result['face_detection'][0]['matches']
    elif len( result['face_detection'] ) > 1:
        # Sometimes ReKognition detects multiple faces when there is
        # only one face.  Keep only the best face.
        best = { 'matches' : None }
        best_confidence = 0

        for face in result['face_detection']:
            if 'matches' in face:
                face_confidence = face['confidence']
                if face_confidence > best_confidence:
                    best_confidence = face_confidence
                    best = face

        return best['matches']
    else:
        return None

def rename_tag_for_user( user_id, old_tag, new_tag, namespace=None ):
    '''Renames all occurrences of old_tag to new_tag for the user.
    Returns the result of the API call in JSON format.

    Raises an exception if the API call does not succeed.'''
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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result
    else:
        raise Exception( result['usage']['status'] )


def train_for_user( user_id, namespace = None ):
    '''Call the ReKognition training API for all faces for the
    user.

    Returns the request result in JSON format.

    Raises an exception if the API call does not succeed.'''

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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result
    else:
        raise Exception( result['usage']['status'] )


def visualize_for_user( user_id, num_img_return_pertag=1, no_image=False, show_default=False, namespace = None ):
    '''Calls the ReKognition Visualize function and returns an array
    of { tag, url, index : ['1', '2', ...] } elements for each tagged
    person.

    Defaults to only one image per person.

    If num_img_return_pertag is None the default ReKognition behavior
    (all tags) is done.

    If no_image is True then no images are generated, only the text
    response is generated.

    If show_default is True then untagged images are included under
    the _x_all tag.

    Raises an exception if the API call does not succeed.'''

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
    result = r.json()
    if result['usage']['status'] == 'Succeed.':
        return result['visualization']
    else:
        raise Exception( result['usage']['status'] )


def detect_for_file( path ):
    '''Calls the ReKognition FaceDetect API and returns a Python data
    structure of the results.

    Return value is a hash with a 'face_detection' array (which can
    have multiple values).  Each face_detection element is a nested
    data structure with may fields.

    The outer structure is a hash, of particular interest is the:
    * confidence

    key.  If at most 1 face was expected, the face with highest
    confidence is probably the one you were searching for.
    '''
    f = open( path )
    image_data = f.read()
    f.close()
    
    data =  {
        "api_key"    : rekog_api_key, 
        "api_secret" : rekog_api_secret,
        "jobs"       : "face_aggressive_beauty",
        "base64"     : base64.b64encode( image_data ),
        }
    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()
        
