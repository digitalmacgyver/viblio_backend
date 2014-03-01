#!/usr/bin/env python

import json
import logging
import os
import random
from sqlalchemy import and_
import uuid

import vib.utils.s3 as s3

from vib.vwf.VWorker import VWorker
import vib.vwf.ActivityDetect.object_classification_driver as oc

import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

class Detect( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'ActivityDetect'
    
    def run_task( self, options ):
        try:
            media_uuid = options['media_uuid']
            user_uuid = options['user_uuid']

            if True and config.VPWSuffix == 'Prod':
                # We don't do activity detection in prod.
                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : 'Skipping activity detection in %s environment.' % ( config.VPWSuffix ) } ) )
                orm = vib.db.orm.get_session()
                orm.commit()
                media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()
                mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
                media.media_workflow_stages.append( mwfs )

                orm.commit()
            
                return { 'media_uuid' : media_uuid,
                         'user_uuid'  : user_uuid }
                

            #activity = random.choice( ['soccer', 'birthday', None ] )
            #activity = 'soccer'
            activity = None

            s3_key = options['Transcode']['output_file']['s3_key']
            s3_bucket = options['Transcode']['output_file']['s3_bucket']
            
            working_dir = os.path.abspath( config.activity_dir + '/' + media_uuid )
            if not os.path.exists( working_dir ):
                os.makedirs( working_dir )
                
            short_name = media_uuid + '/' + media_uuid + '.mp4'
            file_name = os.path.abspath( config.activity_dir + '/' + short_name )

            s3.download_file( file_name, s3_bucket, s3_key )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Testing media %s for soccer activity.' % ( media_uuid ) } ) )
            ( is_soccer, confidence ) = oc.activity_present( file_name, working_dir, config.soccer_model_dir )

            if is_soccer:
                activity = 'soccer'

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Adding activity of %s to media %s' % ( activity, media_uuid ) } ) )

            orm = vib.db.orm.get_session()
            orm.commit()
            media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

            if activity is not None:
                ma = orm.query( MediaAssets ).filter( and_( MediaAssets.media_id == media.id, MediaAssets.asset_type == 'main' ) ).one()
                maf = MediaAssetFeatures( feature_type = 'activity',
                                          coordinates = activity,
                                          detection_confidence = confidence )
                ma.media_asset_features.append( maf )

                user_id = orm.query( Users ).filter( Users.uuid == user_uuid ).one().id

                user_albums = orm.query( Media ).filter( and_( Media.user_id == user_id, Media.is_album == True ) )

                album_names = {}
                for album in user_albums:
                    album_names[album.title] = album
                if activity in album_names:
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'message' : 'Adding media %s to existing album called %s' % ( media_uuid, activity ) } ) )
                    album = album_names[activity]
                    media_album = MediaAlbums( media_id = media.id,
                                               album_id = album_names[activity].id )
                    orm.add( media_album )
                else:
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'message' : 'Creating new album called %s' % ( activity ) } ) )
                    album = Media( user_id = user_id,
                                   uuid    = str( uuid.uuid4() ),
                                   is_album = True,
                                   media_type = 'original',
                                   title = activity )
                    orm.add( album )
                    media_poster = orm.query( MediaAssets ).filter( and_( MediaAssets.asset_type == 'poster', MediaAssets.media_id == media.id ) ).one()
                    poster = MediaAssets( user_id = user_id,
                                          uuid = str( uuid.uuid4() ),
                                          asset_type = 'poster',
                                          mimetype = media_poster.mimetype,
                                          location = media_poster.location,
                                          uri = media_poster.uri, 
                                          width = media_poster.width,
                                          height = media_poster.height )
                    album.assets.append( poster )
                    orm.commit()
                    log.info( json.dumps( { 'media_uuid' : media_uuid,
                                            'user_uuid' : user_uuid,
                                            'message' : 'Adding media %s to newly created album called %s' % ( media_uuid, activity ) } ) )
                    media_album = MediaAlbums( media_id = media.id,
                                               album_id = album.id )
                    orm.add( media_album )
                
            mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
            media.media_workflow_stages.append( mwfs )
            orm.commit()

            return { 'media_uuid' : media_uuid,
                     'user_uuid'  : user_uuid }
            
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Unknown error in activity detection, message was: %s" % e
                        } ) )
            # Hopefully some blip, fail with retry status.
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }



