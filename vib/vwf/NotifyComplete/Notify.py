#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
import hmac
import json
import logging
import requests
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *
from vib.vwf.VWorker import VWorker

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

class Notify( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'NotifyComplete'
    
    def run_task( self, options ):
        '''Send message to CAT to cause user notification.'''

        try:
            media_uuid = options['media_uuid']
            user_uuid = options['user_uuid']

            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : 'Notifying Cat server at %s' %  config.viblio_server_url
                    } ) )
            site_token = hmac.new( config.site_secret, user_uuid ).hexdigest()
            res = requests.get( config.viblio_server_url, params={ 'uid': user_uuid, 'mid': media_uuid, 'site-token': site_token } )
            body = ''
            if hasattr( res, 'text' ):
                body = res.text
            elif hasattr( res, 'content' ):
                body = str( res.content )
            else:
                print 'Error: Cannot find body in response!'
            jdata = json.loads( body )

            if 'error' in jdata:
                log.error( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Error notifying CAT, message was: %s" % jdata['message']
                            } ) )
                # Hopefully some blip, fail with retry status.
                return { 'ACTIVITY_ERROR' : True, 'retry' : True }

            # Check if this is a special video for a new user tesing
            # Photo Finder.
            try:
                if options.get( 'try_photos', False ):
                    orm = vib.db.orm.get_session()
                    orm.commit()

                    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

                    password = user.metadata
                    user.metadata = None
                    orm.commit()

                    album = orm.query( Media ).filter( and_( Media.user_id == user.id, Media.is_viblio_created == True, Media.title == config.try_photos_album_name ) ).one()

                    sqs = boto.sqs.connect_to_region( config.sqs_region, 
                                                      aws_access_key_id = config.awsAccess, 
                                                      aws_secret_access_key = config.awsSecret ).get_queue( config.email_queue )
                    sqs.set_message_class( RawMessage )

                    subject = 'Your photos are ready!'
                    template = 'email/26-photoFinder.tt'

                    message = {
                        'subject' : subject,
                        'to' : [ { 'email' : user.email,
                                   'name' : user.displayname } ],
                        'template': template,
                        'stash' : { 'user' : { 'displayname' : user.displayname },
                                    'model' : { 'media' : [ { 'uuid' : media_uuid,
                                                              'views' : {
                                            'poster' : {
                                                'uri' : options['outputs'][0]['thumbnails'][0]['output_file']['s3_key']
                                                }
                                            }
                                                              }
                                                            ],
                                                'password' : password,
                                                'album_uuid' : album.uuid
                                                }
                                    }
                        }
                        
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'message' : "Sending message format of: %s" % ( message ) } ) )

                    m = RawMessage()
                    m.set_body( json.dumps( message ) )
                    status = sqs.write( m )
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                             'user_uuid' : user_uuid,
                                             'message' : "Message status was: %s" % ( status ) } ) )
            except Exception as e:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "Error while sending try photo finder message: %s" % ( e ) } ) )
                

            # Check if this is special Viblio generated content, if so
            # maybe do something else.
            try:
                if options.get( 'viblio_added_content_type', '' ) in [ 'Smiling Faces', 'Album Summary', config.viblio_summary_video_type ]:
                    orm = vib.db.orm.get_session()
                    orm.commit()

                    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

                    sqs = boto.sqs.connect_to_region( config.sqs_region, 
                                                      aws_access_key_id = config.awsAccess, 
                                                      aws_secret_access_key = config.awsSecret ).get_queue( config.email_queue )
                    sqs.set_message_class( RawMessage )

                    subject = 'VIBLIO Made You a Present'
                    template = 'email/21-mashupGiftForYou.tt'
                    if options['viblio_added_content_type'] == config.viblio_summary_video_type:
                        subject = 'Your Moments Summary VIBLIO Video is Ready'
                        template = 'email/23-momentSummary.tt'

                    if options.get( 'subject', None ) is not None:
                        subject = options['subject']
                    if options.get( 'template', None ) is not None:
                        template = options['template']

                    message = {
                        'subject' : subject,
                        'to' : [ { 'email' : user.email,
                                   'name' : user.displayname } ],
                        'template': template,
                        'stash' : { 'user' : { 'displayname' : user.displayname },
                                    'model' : { 'media' : [ { 'uuid' : media_uuid,
                                                              'views' : {
                                            'poster' : {
                                                'uri' : options['outputs'][0]['thumbnails'][0]['output_file']['s3_key']
                                                }
                                            }
                                                              }
                                                            ]
                                                }
                                    }
                        }
                        
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'message' : "Sending message format of: %s" % ( message ) } ) )

                    m = RawMessage()
                    m.set_body( json.dumps( message ) )
                    status = sqs.write( m )
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                             'user_uuid' : user_uuid,
                                             'message' : "Message status was: %s" % ( status ) } ) )
            except Exception as e:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "Error while sending smiling face message: %s" % ( e ) } ) )

            orm = vib.db.orm.get_session()
            media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

            mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
            media.media_workflow_stages.append( mwfs )
            orm.commit()

            return {}

        except Exception as e:
            log.error( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Unknown error notifying CAT, message was: %s" % e
                        } ) )
            # Hopefully some blip, fail with retry status.
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }



