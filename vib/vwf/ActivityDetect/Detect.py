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

            if True and config.VPWSuffix in [ 'Prod' ]:
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
            activities = []

            s3_key = options['Transcode']['output_file']['s3_key']
            s3_bucket = options['Transcode']['output_file']['s3_bucket']
            
            working_dir = os.path.abspath( config.activity_dir + '/' + media_uuid )
            if not os.path.exists( working_dir ):
                os.makedirs( working_dir )
                
            short_name = media_uuid + '/' + media_uuid + '.mp4'
            file_name = os.path.abspath( config.activity_dir + '/' + short_name )

            s3.download_file( file_name, s3_bucket, s3_key )

            ####################################################
            # Soccer
            ####################################################

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Testing media %s for soccer activity.' % ( media_uuid ) } ) )
            ( is_soccer, confidence ) = oc.activity_present( file_name, working_dir, config.soccer_model_dir )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Value of is_soccer was %s, confidence was %s' % ( is_soccer, confidence ) } ) )


            if is_soccer:
                activities.append( 'soccer' )

                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : 'Adding activity of soccer to media %s' % ( media_uuid ) } ) )

            ####################################################
            # Basketball Shot
            ####################################################
                '''
            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Testing media %s for basketball shot activity.' % ( media_uuid ) } ) )
            ( is_shot, confidence ) = oc.activity_present( file_name, working_dir, config.basketball_shot_model_dir )

            if is_shot:
                activities.append( 'basketball_shot' )

                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : 'Adding activity of basketball_shot to media %s' % ( media_uuid ) } ) )
                                        '''

            ####################################################
            # Christmas
            ####################################################
            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Testing media %s for christmas activity.' % ( media_uuid ) } ) )
            ( is_christmas, confidence ) = oc.activity_present( file_name, working_dir, config.christmas_model_dir )

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Value of is_christmas was %s, confidence was %s' % ( is_christmas, confidence ) } ) )

            if is_christmas:
                activities.append( 'christmas' )

                log.info( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : 'Adding activity of christmas to media %s' % ( media_uuid ) } ) )

            orm = vib.db.orm.get_session()
            orm.commit()
            media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

            for activity in activities:
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
                    already_in_album = orm.query( MediaAlbums ).filter( and_( MediaAlbums.media_id == media.id, MediaAlbums.album_id == album_names[activity].id ) )[:]
                    if len( already_in_album ) == 0:
                        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                                'user_uuid' : user_uuid,
                                                'message' : 'Adding media %s to existing album called %s' % ( media_uuid, activity ) } ) )
                        media_album = MediaAlbums( media_id = media.id,
                                                   album_id = album_names[activity].id )
                        orm.add( media_album )
                    else:
                        log.info( json.dumps( { 'media_uuid' : media_uuid,
                                                'user_uuid' : user_uuid,
                                                'message' : 'Media %s is already in existing album called %s' % ( media_uuid, activity ) } ) )             
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
                orm.commit()

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



