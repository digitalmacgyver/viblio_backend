#!/usr/bin/env python

import boto
from boto.s3.key import Key
import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
import datetime
import json
import logging
from logging import handlers
import os
from PIL import Image
import re
import requests
from StringIO import StringIO
from sqlalchemy import and_
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.rekog.utils as rekog

import vib.db.orm
from vib.db.models import *

log = logging.getLogger( 'vib.fb.CreateContacts' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'fb: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def get_fb_friends_for_user( user_uuid, fb_user_id ):
    '''Given a FB user ID, returns an array of { 'id':...,
    'name':... } pairs.'''

    try:
        data = {
            'access_token' : fb_access_token,
            'fields' : 'id,name,friends'
            }

        r = requests.get( config.fb_endpoint + '%s/' % fb_user_id, params=data )
    
        friends = []
        rdict = r.json()
        if 'friends' in rdict and 'data' in rdict['friends']:
            friends = r.json()['friends']['data']

        print "Returning friends array: %s" % friends

        return friends

    except Exception as e:
        log.exception( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def update_rekognition_for_user( user_uuid, fb_user_id, fb_friends ):
    '''Crawls Facebook for the user and their friends downloading
    tagged face images into ReKognition.

    Renames the tags of the faces in ReKognition to just be the
    Facebook ID of the person

    Returns an array of the crawled faces with:
    { name : ..., facebook_id : ..., rekog_url : ... }
    '''

    try:
        # DEBUG
        print "CRAWLING results"

        # Crawl facebook for images of the friends.
        crawl_results = rekog.crawl_faces_for_user( user_uuid, fb_access_token, fb_user_id, fb_friends )

        # DEBUG
        print crawl_results
        print "TRAINING results"

        # Train on those people (and anyone else present)
        train_results = rekog.train_for_user( user_uuid )
    
        # DEBUG
        print train_results
        print "VISUALIZING results"

        # Get a list of all the people in { tag, url, index : [#,
        # #...] } format
        # 
        # tags for the face_crawled users are like name-facebook_id
        # where name has spaces replace with underscores
        tagged_people = rekog.visualize_for_user( user_uuid )
    
        # DEBUG
        print tagged_people

        results = []

        # Rename the tags to just be the Facebook IDs of the people,
        # and return an array including the URLs to images of their
        # faces.
        for person in tagged_people:
            old_tag = person['tag']        

            # Check if we've already processed this tag, or if it
            # doesn't conform to our expected format.
            if not re.search( r'\-\d+$', old_tag ):
                continue

            old_tag = person['tag']
            facebook_id = old_tag.rpartition( '-' )[-1]
            name = old_tag.rpartition( '-' )[0]
            name = name.replace( '_', ' ' )

            rename_result = rekog.rename_tag_for_user( user_uuid, old_tag, facebook_id )

            print "Adding name: %s, fbid: %s, URL: %s" % ( name, facebook_id, person['url'] )

            results.append( { 'name' : name, 'facebook_id' : facebook_id, 'rekog_url' : person['url'] } )

        return results
    
    except Exception as e:
        log.exception( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def download_faces_for_user( user_uuid, people, directory='/tmp/fb_faces' ):
    '''Given a user_uuid and an array of { facebook_id, rekog_url } elements
    download the image at URL to a file called /dir/user_uuid/tag.jpg
    in the provided dir (defaults to /tmp/fb_faces.

    Returns the people array with modified elements that hold a 'file'
    key referring to the downloaded images cropped to 65x65.'''
    
    try:
        directory += "/" + user_uuid + '/'
        if not os.path.exists( directory ):
            os.makedirs( directory )
            
        for person in people:
            result = requests.get( person['rekog_url'] )
            full_image = Image.open( StringIO( result.content ) )
            cropped_image = full_image.crop( (0, 0, 65, 65 ) )
            filename = "%s%s.png" % ( directory, person['facebook_id'] )
            cropped_image.save( filename )
            person['file'] = filename
                
        return people

    except Exception as e:
        log.exception( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def fb_recent_link_request( user_uuid, hours=2 ):
    '''Returns true if the user_uuid has had a FB link created within
    the last "hours" number of hours, defaults to 2'''

    try:
        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

        from_when = datetime.datetime.utcnow() - datetime.timedelta( hours=hours )

        result = orm.query( Links ).filter( and_( Links.user_id == user.id, Links.created_date > from_when ) )
        
        return result.count() == 1

    except Exception as e:
        log.exception( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise


def __get_s3_bucket():
    try:
        if not hasattr( __get_s3_bucket, "bucket" ):
            __get_s3_bucket.bucket = None
        if __get_s3_bucket.bucket == None:
            s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
            __get_s3_bucket.bucket = s3.get_bucket( config.bucket_name )
        return __get_s3_bucket.bucket
    except Exception as e:
        log.error( json.dumps( { 
                    "message" : 'Failed to obtain s3 bucket: %s' % e
                    } ) )
        raise

def upload_file_to_s3( filename, s3_key ):
    '''Upload a file to S3'''
    try:
        bucket = __get_s3_bucket()
        k = Key( bucket )
        k.key = s3_key
        k.set_contents_from_filename( filename )
    except Exception as e:
        log.error( json.dumps( { 
                    "message" : 'Failed to upload %s to s3: %s' % ( filename, e )
                    } ) )
        raise

def add_contacts_for_user( user_uuid, people ):
    '''Takes in a user_uuid and an array of { tag, name, file }
    elements.

    For each id present in the attay, if no such contact exists for
    that user with a provider/provider_id of facebook/id:
    * The file is uploaded to s3

    * A media/media_asset/media_asset_feature with 'fb_face' types are
      created.

    * The picture URI is set to the S3 location.

    Returns an array of the people for whom contacts where created.
    '''

    try:
        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

        contacts = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.provider == 'facebook' ) )

        existing_contacts = {}
        for contact in contacts:
            if contact.provider_id is None:
                log.exception( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Found contact id %s for user_uuid %s with provier of facebook but no provider_id" % ( contact.id, user_uuid )
                            } ) )
            else:
                existing_contacts[ contact.provider_id ] = contact

        print "Existing contacts keys are: %s" % existing_contacts.keys()

        created_contacts = []

        # Okay... Adding MAFs for this causes GUI server exceptions.
        # Maybe that's for the best.
        # For the time being just add a picture URI and forget the rest.
        
                
        for friend in people:
            if friend['facebook_id'] not in existing_contacts:
                print "Inserting new contact on %s: " % friend['facebook_id']
                media_uuid = str( uuid.uuid4() )
                s3_key = "%s/%s_fb_face.png" % ( media_uuid, media_uuid )
                upload_file_to_s3( friend['file'], s3_key )

                contact = Contacts(
                    uuid         = str( uuid.uuid4() ),
                    user_id      = user.id,
                    contact_name = friend['name'],
                    provider     = 'facebook',
                    provider_id  = friend['facebook_id'],
                    picture_uri  = s3_key
                    )

                #media = Media( 
                #    uuid       = media_uuid,
                #    media_type = 'fb_face'
                #    )

                #user.media.append( media )

                #media_asset = MediaAssets(
                #    uuid       = str( uuid.uuid4() ),
                #    asset_type = 'fb_face',
                #    mimetype   = 'image/png',
                #    bytes      = os.path.getsize( friend['file'] ),
                #    uri        = s3_key,
                #    location   = 'us'
                #    )
                #media.assets.append( media_asset )

                #media_asset_feature = MediaAssetFeatures(
                #    feature_type = 'fb_face',
                #    )
                
                #media_asset.media_asset_features.append( media_asset_feature )
                #contact.media_asset_features.append( media_asset_feature )
                
                created_contacts.append( friend )
            else:
                log.debug( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Contact for facebook friend %s / %s already exists, skipping." % ( friend['name'], friend['tag'] )
                            } ) )


        orm.commit()
        return created_contacts
    
    except Exception as e:
        orm.rollback()
        log.exception( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

# Main logic.

fb_access_token = 'CAAGwcWaZA3SsBANSdWla6CVeIJ5NeFI4ai3OQeZAwQHV2aVCzZC4HkZAZACC3yLj1is6816LkiQTLKfTkP2rlXwcTOdHigAwt6GcppIA7NzWFu4qIkVkQQkzjxMYX6xzEWWplp63EomqtWWbVaDyzjVxzNSymKselb1RXbOTZCZA5sMkgtyDcZBlFURo4dRdz5wZD'

fb_user_id = '100006092460819'

#user_uuid = '08CC5BC0-3856-11E3-BF24-4155F9A9DC36'
user_uuid = '08CC5BC0-3856-11E3-BF24-4155F9A9DC35'

# DEBUG - TODO
# 1. Get the hello world version working
# 2. In another file hello world the queue poll.
# 3. Test adding stuff to the queue manually.
# 4. Delete temporary files
# 5. Wrap it in a while loop and make a supervisor config.
# 6. Deploy it and test adding to the queue manually.

sqs = __get_sqs().get_queue( config.fb_link_queue )

def run():
    try:
        message = sqs.read( wait_time_seconds = 20 )
        
        options = json.loads( message.get_body() )
        
        fb_access_token = options['fb_access_token']
        fb_user_id      = options['fb_user_id']
        user_uuid       = options['user_uuid']

        # DEBUG
        #if fb_recent_link_request( user_uuid ):
        if True:
            print "Getting FB friends"
            friends = get_fb_friends_for_user( user_uuid, fb_user_id )
            import pprint
            pp = pprint.PrettyPrinter( indent=4 )
            pp.pprint( friends )

            print "Getting ReKognition People"
            people = update_rekognition_for_user( user_uuid, fb_user_id, friends )
            # DEBUG - keep our API limits low for testing.
            #fb_user_id = '621782016'
            #people = update_rekognition_for_user( user_uuid, fb_user_id, [] )
            pp.pprint( people )
    
            print "Getting Downloaded Files"
            people_files = download_faces_for_user( user_uuid, people )
            pp.pprint( people_files )
            
            print "Adding contacts to database."
            added_contacts = add_contacts_for_user( user_uuid, people_files )
            pp.pprint( added_contacts )

        sqs.delete_message( message )

        return True

    except Exception as e:
        log.exception( json.dumps( {
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

