#!/usr/bin/env python

import boto
from boto.s3.key import Key
import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
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

def get_fb_friends_for_user( user_uuid, fb_user_id, fb_access_token ):
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

        return friends

    except Exception as e:
        log.error( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def update_rekognition_for_user( user_uuid, fb_user_id, fb_friends, fb_access_token ):
    '''Crawls Facebook for the user and their friends downloading
    tagged face images into ReKognition.

    Renames the tags of the faces in ReKognition to just be the
    Facebook ID of the person

    Returns an array of the crawled faces with:
    { name : ..., facebook_id : ..., rekog_url : ... }
    '''

    try:
        # Crawl facebook for images of the friends.
        crawl_friends = []

        existing_contacts = get_existing_fb_contacts_for_user( user_uuid )
        skip_self = False

        if fb_user_id in existing_contacts:
            skip_self = True
            log.warning( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "Found self %s in contact list, skipping." % fb_user_id
                        } ) )


        for friend in fb_friends:
            if friend['id'] in existing_contacts:
                log.warning( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Found existing contact %s in friend list, skipping." % friend['id']
                            } ) )
            else:
                crawl_friends.append( friend )

                
        crawl_results = rekog.crawl_faces_for_user( user_uuid, fb_access_token, fb_user_id, crawl_friends, skip_self=skip_self )

        log.debug( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "ReKognition FaceCrawl results: %s" % crawl_results
                    } ) )

        # Train on those people (and anyone else present)
        train_results = rekog.train_for_user( user_uuid )
    
        log.debug( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "ReKognition FaceTrain results: %s" % train_results
                    } ) )

        # Get a list of all the people in { tag, url, index : [#,
        # #...] } format
        # 
        # tags for the face_crawled users are like name-facebook_id
        # where name has spaces replace with underscores
        tagged_people = rekog.visualize_for_user( user_uuid )
    
        log.debug( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "ReKognition FaceVisualize results: %s" % tagged_people
                    } ) )

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

            log.debug( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "Found name: %s, facebook_id: %s, url: %s" % ( name, facebook_id, person['url'] )
                        } ) )

            results.append( { 'name' : name, 'facebook_id' : facebook_id, 'rekog_url' : person['url'] } )

        return results
    
    except Exception as e:
        log.error( json.dumps( {
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
        log.error( json.dumps( {
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
        log.error( json.dumps( {
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

def get_existing_fb_contacts_for_user( user_uuid ):
    try:
        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

        contacts = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.provider == 'facebook' ) )

        existing_contacts = {}
        for contact in contacts:
            if contact.provider_id is None:
                log.error( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Found contact id %s for user_uuid %s with provider of facebook but no provider_id" % ( contact.id, user_uuid )
                            } ) )
            else:
                existing_contacts[ contact.provider_id ] = contact

        orm.commit()

        return existing_contacts
    except Exception as e:
        orm.rollback()
        log.error( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def add_contacts_for_user( user_uuid, people, fb_friends ):
    '''Takes in a user_uuid and an array of { facebook_id, name, file
    } elements, and an array of { id, name } elements

    For each id present in the first array, if no such contact exists
    for that user with a provider/provider_id of facebook/id:

    * The file is uploaded to s3

    * A media/media_asset/media_asset_feature with 'fb_face' types are
      created.

    * The picture URI is set to the S3 location.

    For each id present in the second array, if it was not in the
    first array and no such contact exists for that user with a
    provider/provider_id of facebook/id a contact is created with no
    picture.

    Returns an array of the people for whom contacts where created.
    '''

    try:
        existing_contacts = get_existing_fb_contacts_for_user( user_uuid )

        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.uuid == user_uuid )[0]

        log.debug( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Existing contacts keys are: %s" % existing_contacts.keys()
                    } ) )

        created_picture_contacts = []
        picture_created = {}
        
        # Okay... Adding MAFs for this causes GUI server exceptions.
        # Maybe that's for the best.
        # For the time being just add a picture URI and forget the rest.
        for friend in people:
            if friend['facebook_id'] not in existing_contacts:

                log.debug( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Inserting new picture contact for id/uuid %s/%s on %s: " % ( user.id, user.uuid, friend['facebook_id'] )
                            } ) )

                picture_created[ friend['facebook_id'] ] = True
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

                orm.add( contact )
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
                
                created_picture_contacts.append( friend )
            else:
                log.debug( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Contact for facebook friend %s / %s already exists, skipping." % ( friend['name'], friend['facebook_id'] )
                            } ) )

        created_empty_contacts = []

        for friend in fb_friends:
            if friend['id'] not in existing_contacts and friend['id'] not in picture_created:

                log.debug( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Inserting new empty contact for id/uuid %s/%s on %s: " % ( user.id, user.uuid, friend['id'] )
                            } ) )

                contact = Contacts(
                    uuid         = str( uuid.uuid4() ),
                    user_id      = user.id,
                    contact_name = friend['name'],
                    provider     = 'facebook',
                    provider_id  = friend['id']
                    )

                orm.add( contact )
                
                created_empty_contacts.append( friend )
            else:
                log.debug( json.dumps( {
                            'user_uuid' : user_uuid,
                            'message' : "Contact for facebook friend %s / %s already exists, skipping." % ( friend['name'], friend['id'] )
                            } ) )

        orm.commit()
        return created_picture_contacts, created_empty_contacts
    
    except Exception as e:
        orm.rollback()
        log.error( json.dumps( {
                    'user_uuid' : user_uuid,
                    'message' : "Exception was: %s" % e
                    } ) )
        raise

def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

# DEBUG
# 4. Delete temporary files

sqs = __get_sqs().get_queue( config.fb_link_queue )
sqs.set_message_class( RawMessage )

def run():
    try:
        message = None
        message = sqs.read( wait_time_seconds = 20 )
        
        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()
        
        try:
            log.debug( json.dumps( {
                        'message' : "Starting CreateContacts, message body was %s: " % body
                        } ) )
        except Exception as e:
            log.debug( json.dumps( {
                        'message' : "Error converting body to string, error was: %s" % e
                        } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( {
                        'message' : "Options are %s: " % options
                        } ) )
        except Exception as e:
            log.debug( json.dumps( {
                        'message' : "Error converting options to string: %e" % e
                        } ) )
        
        fb_access_token = options['fb_access_token']
        fb_user_id      = options['facebook_id']
        user_uuid       = options['user_uuid']

        # DEBUG
        if fb_recent_link_request( user_uuid ):
        #if True:
            friends = get_fb_friends_for_user( user_uuid, fb_user_id, fb_access_token )
            log.debug( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "Facebook friends for user %s/%s were %s" % ( user_uuid, fb_user_id, friends ) 
                        } ) )

            people = update_rekognition_for_user( user_uuid, fb_user_id, friends, fb_access_token )
            # DEBUG - keep our API limits low for testing.
            #people = update_rekognition_for_user( user_uuid, fb_user_id, [] )
            log.debug( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "People from ReKognition for user %s/%s were %s" % ( user_uuid, fb_user_id, people ) 
                        } ) )
    
            people_files = download_faces_for_user( user_uuid, people )
            log.debug( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "Downloaded files for user %s/%s were %s" % ( user_uuid, fb_user_id, people_files ) 
                        } ) )
            
            ( added_picture_contacts, added_empty_contacts ) = add_contacts_for_user( user_uuid, people_files, friends )
            log.debug( json.dumps( {
                        'user_uuid' : user_uuid,
                        'message' : "For user %s/%s added picture contacts %s and non-picture contacts %s" % ( user_uuid, fb_user_id, added_picture_contacts, added_empty_contacts ) 
                        } ) )

        sqs.delete_message( message )

        return True

    except Exception as e:
        log.error( json.dumps( {
                    'message' : "Exception was: %s" % e
                    } ) )
        raise
    finally:
        if message != None:
            sqs.delete_message( message )

