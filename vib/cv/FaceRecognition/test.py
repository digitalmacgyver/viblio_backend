#!/usr/bin/env python

import base64
import os
import re
import requests

bidyut = '/wintmp/f/b/'
mona   = '/wintmp/f/m/'
other  = '/wintmp/f/o/'
ramsri = '/wintmp/f/r/'

# Bidyut:
# 1313, 0,1,9
# 2147, 0
# 2898, 0, 16
# 3536, 4
# 3622, 1

# Elements are hashes with file, person names
test_files = []

api_key = 'UpNFfyP7ttEhxya5'
api_secret = 'b37NhBxCcbSC7LQ5'

namespace = 'layers'

def face_recognize( path ):
    user_id = 'l1'

    f = open( path )
    image_data = f.read()
    f.close()

    data =  {
        "api_key"    : api_key,
        "api_secret" : api_secret,
        "jobs"       :"face_recognize",
        "base64"     : base64.b64encode(image_data),
        "name_space" : namespace,
        'user_id'    : user_id
        }
 
    r = requests.post( "http://rekognition.com/func/api/" , data )
    print r.json()
    return r.json()

def add_l1( filename, name ):
    user_id = 'l1'
    f = open( filename )
    image_data = f.read()
    f.close()
    data =  {
	    "api_key"    : api_key, 
	    "api_secret" : api_secret,
	    "jobs"       : "face_add",
	    "base64"     : base64.b64encode(image_data),
	    "name_space" : namespace,
            'tag'        : name,
            'user_id'    : user_id
	    }
    r = requests.post( "http://rekognition.com/func/api/", data )
    print "Working on ", filename
    print r.json()
    return r.json()

#add_l1( '/wintmp/f/b/1313_9_3964.jpg', 'bidyut' )
#add_l1( '/wintmp/f/m/3053_0_3566.jpg', 'mona' )
#add_l1( '/wintmp/f/r/2898_9_3288.jpg', 'ramsri' )

def add_l2( filename, name ):
    user_id = 'l2_' + name
    f = open( filename )
    image_data = f.read()
    f.close()
    data =  {
	    "api_key"    : api_key, 
	    "api_secret" : api_secret,
	    "jobs"       : "face_add",
	    "base64"     : base64.b64encode(image_data),
	    "name_space" : namespace,
            'user_id'    : user_id
	    }
    r = requests.post( "http://rekognition.com/func/api/", data )
    print "Working on ", filename
    print r.json()
    return r.json()

def face_cluster( name, aggressiveness = None ):
    user_id = 'l2_' + name
    data = {
        "api_key"    : api_key,
        "api_secret" : api_secret,
        "jobs"       : "face_cluster",
        "name_space" : namespace,
        'user_id'    : user_id,
        'aggressiveness' : aggressiveness
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json() 

# Bidyut
# 1313_9_3964
# 74.8937

for face in os.listdir( bidyut ):
    if face.endswith( '.jpg' ):
        ( media, track, asset ) = re.match( r'(\d+)_(\d+)_(\d+)\.jpg', face ).groups()
        if media == '1313':
            if track in '1':
                test_files.append( {
                        'filename' : bidyut + face,
                        'name'     : 'bidyut'
                        } )
            else:
                pass #add_l2( filename = bidyut + face, name = 'bidyut' )
        elif media == '2147':
            test_files.append( {
                    'filename' : bidyut + face,
                    'name'     : 'bidyut'
                    } )
        elif media == '2898':
            if track == '0':
                test_files.append( {
                        'filename' : bidyut + face,
                        'name'     : 'bidyut'
                        } )
            else:
                pass #add_l2( filename = bidyut + face, name = 'bidyut' )
        elif media == '3536':
            test_files.append( {
                    'filename' : bidyut + face,
                    'name'     : 'bidyut'
                    } )
        elif media == '3622':
            pass #add_l2( filename = bidyut + face, name = 'bidyut' )

#result = face_cluster( 'bidyut' )
#print result

# Mona:
# 3053, 0,1,2
# 3055, 1
# 3070, 0,2
# 3102, 0
# 3103, 0

# 3053_0_3566
# 58.0944

for face in os.listdir( mona ):
    if face.endswith( '.jpg' ):
        ( media, track, asset ) = re.match( r'(\d+)_(\d+)_(\d+)\.jpg', face ).groups()
        if media == '3053':
            if track in '1':
                test_files.append( {
                        'filename' : mona + face,
                        'name'     : 'mona'
                        } )
            else:
                pass #add_l2( filename = mona + face, name = 'mona' )
        elif media == '3055':
            test_files.append( {
                    'filename' : mona + face,
                    'name'     : 'mona'
                    } )
        elif media == '3070':
            if track == '0':
                test_files.append( {
                        'filename' : mona + face,
                        'name'     : 'mona'
                        } )
            else:
                pass #add_l2( filename = mona + face, name = 'mona' )
        elif media == '3102':
            test_files.append( {
                    'filename' : mona + face,
                    'name'     : 'mona'
                    } )
        elif media == '3103':
            pass #add_l2( filename = mona + face, name = 'mona' )

#result = face_cluster( 'mona' )
#print result

# Ramsri:
# 2147, 1
# 2898, 9
# 3009, 0
# 3010, 0

# 2898_9_3288
# 65.2904

for face in os.listdir( ramsri ):
    if face.endswith( '.jpg' ):
        ( media, track, asset ) = re.match( r'(\d+)_(\d+)_(\d+)\.jpg', face ).groups()
        if media == '2147':
            if track in '1':
                test_files.append( {
                        'filename' : ramsri + face,
                        'name'     : 'ramsri'
                        } )
        elif media == '3009':
            test_files.append( {
                    'filename' : ramsri + face,
                    'name'     : 'ramsri'
                    } )
        elif media == '3010':
            pass #add_l2( filename = ramsri + face, name = 'ramsri' )
        elif media == '2898':
            pass #add_l2( filename = ramsri + face, name = 'ramsri' )

#result = face_cluster( 'ramsri' )
#print result

for test in test_files:
    filename = test['filename']
    who = test['name']

    print "Checking match for %s, %s" % ( who, filename )

    face_recognize( filename )

for filename in os.listdir( other ):
    print "Checking match for other, %s" % ( other + filename )
    
    face_recognize( other + filename )
