#!/usr/bin/env python

import json
import logging
from logging import handlers
import re
import requests
from sqlalchemy import and_
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *

logger = logging.getLogger( 'vib.fb.CreateContacts' )
logger.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'fb: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

logger.addHandler( syslog )
logger.addHandler( consolelog )

rekog_api_key = config.rekog_api_key
rekog_api_secret = config.rekog_api_secret

fb_access_token = 'CAAGwcWaZA3SsBANSdWla6CVeIJ5NeFI4ai3OQeZAwQHV2aVCzZC4HkZAZACC3yLj1is6816LkiQTLKfTkP2rlXwcTOdHigAwt6GcppIA7NzWFu4qIkVkQQkzjxMYX6xzEWWplp63EomqtWWbVaDyzjVxzNSymKselb1RXbOTZCZA5sMkgtyDcZBlFURo4dRdz5wZD'

namespace = config.rekog_namespace

fb_user = '100006092460819'

user_uuid = '08CC5BC0-3856-11E3-BF24-4155F9A9DC35'

def get_fb_friends( fb_user ):
    '''Given a FB user ID, returns an array of { 'id':...,
    'name':... } pairs.'''

    data = {
        'access_token' : fb_access_token,
        'fields' : 'id,name,friends'
        }

    r = requests.get( config.fb_endpoint + '%s/' % fb_user, params=data )
    
    freinds = []
    rdict = r.json()
    if 'friends' in rdict and 'data' in rdict['friends']:
        friends = r.json()['friends']['data']

    print "Returning friends array: %s" % friends

    return friends

def update_rekognition( fb_user, fb_friends ):
    '''Crawls Facebook for the user and their friends downloading
    tagged face images into ReKognition.

    Renames the tags of the faces in ReKognition to just be the
    Facebook ID of the person

    Returns an array of the crawled faces with:
    { name : ..., facebook_id : ..., rekog_url : ... }
    '''
    
    # DEBUG - Handle if there are more than 20 friends.

    # First crawl the faces.
    jobs = 'face_crawl_[' + fb_user
    for friend in fb_friends:
        jobs += ';' + friend['id']
    jobs += ']'

    print "Job was %s" % jobs

    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : jobs,
        'fb_id'        : fb_user,
        'access_token' : fb_access_token,
        'name_space'   : namespace,
        'user_id'      : user_uuid
        }

    r = requests.post( "http://rekognition.com/func/api/", data )
    print "Crawl result was %s" % r.json()

    # Then get a list of all the faces.
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : 'face_visualize',
        'num_img_return_pertag' : 1,
        'name_space'   : namespace,
        'user_id'      : user_uuid
        }

    r = requests.post( "http://rekognition.com/func/api/", data )

    tagged_people = r.json()['visualization']
    print "Vizualize result was %s" % r.json()
    
    # Then build our output
    result = []

    for person in tagged_people:
        old_tag = person['tag']        

        # Check if we've already processed this tag, or if it doesn't
        # conform to our expected format.
        if not re.search( r'\-\d+$', old_tag ):
            continue

        old_tag = person['tag']
        facebook_id = old_tag.rpartition( '-' )[-1]
        name = old_tag.rpartition( '-' )[0]
        name.replace( '_', ' ' )

        data = {
            'api_key'      : rekog_api_key,
            'api_secret'   : rekog_api_secret,
            'jobs'         : 'face_rename',
            'tag'          : old_tag,
            'new_tag'      : facebook_id,
            'name_space'   : namespace,
            'user_id'      : user_uuid
            }

        r = requests.post( "http://rekognition.com/func/api/", data )

        print "Adding name: %s, fbid: %s, URL: %s" % ( name, facebook_id, person['url'] )

        result.append( { 'name' : name, 'facebook_id' : facebook_id, 'rekog_url' : person['url'] } )

    return result

def add_contacts_for_user( user_uuid, friends ):
    '''Takes in a user_uuid and an array of { id : ..., name : ... }
    friends and creates contacts for the friends.  Returns an array of
    { id : ..., name : ... contacts that were added'''

    orm = vib.db.orm.get_session()

    user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

    contacts = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.provider == 'facebook' ) )

    existing_contacts = {}
    for contact in contacts:
        if contact.provider_id is None:
            # DEBUG log an error
            pass
        else:
            existing_contacts[ contact.provider_id ] = contact

    for friend in friends:
        if friend['id'] not in existing_contacts:
            pass
    

friends = get_fb_friends( fb_user )
import pprint
pp = pprint.PrettyPrinter( indent=4 )
pp.pprint( friends )

result = update_rekognition( fb_user, friends )
print result

# Here is how to convert an image:
#/usr/bin/convert -crop 65x65+0+0\! foo.jpg cropX.jpg


#result = add_contacts_for_user( user_uuid, friends )



