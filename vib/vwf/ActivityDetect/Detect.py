#!/usr/bin/env python

import json
import logging
import random
from sqlalchemy import and_

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

            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : 'Adding activity of %s to media %s' % ( activity, media_uuid ) } ) )

            if activity is not None:
                self.heartbeat()
                orm = vib.db.orm.get_session()
                media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

                ma = orm.query( MediaAssets ).filter( and_( MediaAssets.media_id == media.id, MediaAssets.asset_type == 'main' ) ).one()
                maf = MediaAssetFeatures( feature_type = 'activity',
                                          coordinates = activity,
                                          detection_confidence = 1 )
                ma.media_asset_features.append( maf )

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



