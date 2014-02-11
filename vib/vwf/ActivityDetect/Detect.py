#!/usr/bin/env python

import json
import logging
import random
from sqlalchemy import and_
import uuid

from vib.vwf.VWorker import VWorker

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

            activity = random.choice( ['soccer', 'birthday', None ] )

            activity = 'soccer'

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Adding activity of %s to media %s' % ( activity, media_uuid ) } ) )

            #import pdb
            #pdb.set_trace()

            if activity is not None:
                self.heartbeat()
                orm = vib.db.orm.get_session()
                orm.commit()
                media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

                ma = orm.query( MediaAssets ).filter( and_( MediaAssets.media_id == media.id, MediaAssets.asset_type == 'main' ) ).one()
                maf = MediaAssetFeatures( feature_type = 'activity',
                                          coordinates = activity,
                                          detection_confidence = 1 )
                ma.media_asset_features.append( maf )

                user_id = orm.query( Users ).filter( Users.uuid == user_uuid ).one().id

                user_albums = orm.query( Media ).filter( and_( Media.user_id == user_id, Media.is_album == True ) )

                album_names = {}
                for album in user_albums:
                    album_names[album.title] = album
                if activity in album_names:
                    album = orm.query( Media ).filter( Media.id == album_group.album_id ).one()
                    media_album = MediaAlbums( media_id = media.id,
                                               album_id = album_names[activity].id )
                    orm.add( media_album )

                else:
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
                    media_album = MediaAlbums( media_id = media.id,
                                               album_id = album.id )
                    orm.add( media_album )
                

                mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
                media.media_workflow_stages.append( mwfs )

                orm.commit()
                self.heartbeat()

            if False:
                return { 'ACTIVITY_ERROR' : True, 'retry' : True }
            else:
                return { 'media_uuid' : media_uuid,
                         'user_uuid'  : user_uuid }
            
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Unknown error in activity detection, message was: %s" % e
                        } ) )
            # Hopefully some blip, fail with retry status.
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }



