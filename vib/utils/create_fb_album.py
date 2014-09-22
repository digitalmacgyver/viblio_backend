#!/usr/bin/env python

'''
{
    'images[]' : [ # Array of images the user selected.
        image1_uuid,
        image2_uuid,
        ... ],
    'access_token' : 'sadfkb234lsdfhdsfkjh234' # A current OAuth token
					   # with the requisite
					   # permissions to publish on
					   # behalf of the user.
					  
# Optional parameters:

# Summary metadata:
    'title' : 'Fun Times!', # OPTIONAL: A title for the album -
			    # defaults to "VIBLIO Photo Summary -
			    # YYYY-MM-DD" - I suggest the UI overwrite
			    # this with "VIBLIO FilterName Summary"
    'description' : "Vacation", # OPTIONAL: A description for the
				# album - defaults to nothing.
}
'''

import boto.swf.layer2 as swf
import boto.sqs
import boto.sqs.connection
from boto.sqs.message import RawMessage
import commands
import glob
import hmac
import os
import json
import logging
from logging import handlers
import re
import requests
import shutil
from sqlalchemy import and_, not_, or_
import sys
import time
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'create_fb_album: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

def run():
    try:
        sqs = __get_sqs().get_queue( config.create_fb_album_queue )
        sqs.set_message_class( RawMessage )

        message = None
        message = sqs.read( wait_time_seconds = 20 )

        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()

        try:
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body %s: " % body } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % e } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % options } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %s" % e } ) )
        
        if 'action' not in options or options['action'] != 'create_fb_album':
            # This message is not for us, move on.
            return True;

        user_uuid       = options['user_uuid']
        images          = options['images[]']
        fb_token    = options['fb_token']
        album_id = options['fb_album_id']
        fb_url = options['fb_album_url']
        title = options.get( 'title', '' )
        # Note - Facebook requires that you not auto populate
        # descriptive fields, or they may consider it spam, so if we
        # didn't get a description don't send any in the request.
        description     = options.get( 'description', )

        # We need to delete the message here or it will reach its
        # visibility timeout and be processed again by other systems.
        # 
        # Album creation is "best effort" in this regard - if we
        # fail we don't try again.
        sqs.delete_message( message )

        media_uuid = str( uuid.uuid4() )

        orm = vib.db.orm.get_session()
        orm.commit()

        images = orm.query( MediaAssets ).filter( 
            MediaAssets.uuid.in_( images ) ).order_by( MediaAssets.created_date.desc() ).all()

        user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

        if len( images ) == 0:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "No images found in database for input, skipping: %s" % images } ) )
            return True
        
        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                'message' : "Working on Facebook album ID: %s, URL: %s" % ( album_id, fb_url ) } ) )
        
        # Upload the images.
        for image in images:
            try:
                upload_image_url = config.fb_endpoint + "%s/photos/?access_token=%s" % ( album_id, fb_token )
                data = { 'url' : "%s%s" % ( config.ImageServer, image.uri ) }
                r = requests.post( upload_image_url, data )
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'message' : "Uploaded photo %s with fb id: %s" % ( image.uri, r.json()['id'] ) } ) )
            except Exception as e:
                # Don't raise an error here, just upload as many images as we can.
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'message' : "Error uploading image %s: %s" % ( image.uuid, e ) } ) )
                
        # Create database records.
        media = Media( uuid = media_uuid,
                       media_type = 'fb_album',
                       title = title,
                       description = description,
                       status = 'complete' )
        user.media.append( media )
                
        asset_uuid = str( uuid.uuid4() )
        media_asset = MediaAssets( uuid = asset_uuid,
                                   asset_type = 'fb_album',
                                   uri = fb_url,
                                   location = 'facebook',
                                   provider = 'facebook',
                                   provider_id = album_id )
        media.assets.append( media_asset )
        orm.commit()

        # Send a notification to the user via email.
        try:
            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Notifying Cat server of album creation at %s' %  config.create_fb_album_url } ) )
            site_token = hmac.new( config.site_secret, user_uuid ).hexdigest()
            res = requests.get( config.create_fb_album_url, params={ 'uid': user_uuid, 'mid': media_uuid, 'site-token': site_token } )
            body = ''
            if hasattr( res, 'text' ):
                body = res.text
            elif hasattr( res, 'content' ):
                body = str( res.content )
            else:
                print 'Error: Cannot find body in response!'
            jdata = json.loads( body )

            if 'error' in jdata:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "Error notifying CAT, message was: %s" % jdata['message'] } ) )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'message' : "Error sending email notification to user: %s" % ( e ) } ) )

        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                'message' : "Completed successfully for fb_album: %s / media_uuid: %s" % ( album_id, media_uuid ) } ) )

        return True

    except Exception as e:
        log.error( json.dumps( { 'message' : "Exception was: %s" % e } ) )
        raise
    finally:
        if message != None and options != None:
            # Even if something went wrong, make sure we delete the
            # message so we don't end up stuck in an infinite loop
            # trying to process this message.
            sqs.delete_message( message )    
