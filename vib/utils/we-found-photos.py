#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
from sqlalchemy import and_
import json
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *

'''This simple wrapper script sends a specific tempalted email to
users to let them know that we have found photos in their account to
incent them to log in and upload some more videos.
'''

def get_connection():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

conn = get_connection()

q = conn.get_queue( config.email_queue )
q.set_message_class( RawMessage )


user_emails = [
    'abigael.smith98@gmail.com',
    'acchou2@gmail.com',
    'amyribar@hotmail.com',
    'annie@hiplegal.com',
    'ayelet@drhirshfeld.com',
    'chrisalb@cineminit.com',
    'chris_clark@mac.com',
    'cmwilliams82@aol.com',
    'cowles@dpw.com',
    'creeks1de@outlook.com',
    'delandkristin@hotmail.com',
    'ejhmb@aol.com',
    'elizabethalathrop@gmail.com',
    'jgsommer@pacbell.net',
    'loolithabalan@gmail.com',
    'marikagroleau@gmail.com',
    'meghan.ingle@gmail.com',
    'mysoupishot@gmail.com',
    'noelle.roux@gmail.com',
    'noshishahid13@gmail.com',
    'richardzhwang@gmail.com',
    'ruby_y@yahoo.com',
    'sonya.ganayni@gmail.com',
    's_amir_@hotmail.com',
    'tkokesh@mac.com',
    'victorialcrane@gmail.com',
    'russell174@gmail.com',
    'catchpolester@gmail.com',
    'krhodes41198@yahoo.com',
    'hyma_menon@hotmail.com',
    'dpalarchio@indigo.ca'
]    

user_emails = [
    'matt@viblio.com'
]

for user_email in user_emails:
    print "Working on: %s" % ( user_email )

    try:
        m = RawMessage()

        orm = vib.db.orm.get_session()

        user = orm.query( Users ).filter( Users.email == user_email ).one()

        user_uuid = user.uuid

        ## Get a list of videos??
        media_files = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.status == 'complete', Media.is_viblio_created == False ) ).order_by( Media.recording_date.desc() )[:2]

        media = []
        for mf in media_files:
            media_uuid = mf.uuid
            uri = [ x.uri for x in mf.assets if x.asset_type == 'poster' ][0]
            media.append( { 'uuid' : media_uuid,
                            'views' : {
                                'poster' : { 
                                    'uri' : uri
                                }
                            }
                        } )
            
            
        if not ( len( media ) >= 1 ):
            print "No movies found for user!"
            continue

        subject = "Don't forget to check out the photos we found"
        template = 'email/26-02-youveGotPhotos.tt'

        message = {
            'subject' : subject,
            'to' : [ { 'email' : user.email,
                       'name' : user.displayname } ],
            'template': template,
            'stash' : { 'user' : { 'displayname' : user.displayname,
                                   'email' : user.email,
                                   'provider' : user.provider },
                        'model' : { 'media' : media },
                    }
        }
        
        m = RawMessage()
        m.set_body( json.dumps( message ) )
        status = q.write( m )
        
        print "Message status was: %s" % ( status )
        
    except Exception as e:
        print "ERROR while sending message: %s" % ( e )
