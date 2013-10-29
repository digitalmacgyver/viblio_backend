#!/usr/bin/env python

import json
import logging
import uuid
from sqlalchemy import and_

import vib.db.orm
from vib.db.models import *

log = logging.getLogger( __name__ )

def add_media_asset_face( user_uuid, media_uuid, s3_key, byte_size, track_id, face ):
    
    try:
        orm = vib.db.orm.get_session()
        media = orm.query( Media ).filter( Media.uuid == media_uuid )[0]

        face_asset = MediaAssets( 
            uuid         = str( uuid.uuid4() ),
            asset_type   = 'face',
            mimetype     = 'image/jpg',
            bytes        = byte_size,
            uri          = s3_key,
            location     = 'us',
            view_count   = 0 )
        media.assets.append( face_asset )
        print face['face_confidence']
        print track_id

        face_feature = MediaAssetFeatures( feature_type           = 'face',
                                            coordinates            = json.dumps( face ),
                                            detection_confidence   = face['face_confidence'],
                                            track_id               = track_id )
        face_asset.media_asset_features.append( face_feature )

        orm.commit()
    except Exception as e:
        log.warning( json.dumps( {
                    'user_uuid' : user_uuid,
                    'media_uuid' : media_uuid,                    
                    'message' : "Exception in adding face to DB: %s" % e
                    } ) )
        orm.rollback()
        raise
    
    return True