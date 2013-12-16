#!/usr/bin/env python

import csv
from sqlalchemy import and_, not_

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

orm = vib.db.orm.get_session()

bad_images = orm.query( MediaAssets.uri,
                        MediaAssetFeatures.media_id,
                        MediaAssetFeatures.track_id,
                        MediaAssetFeatures.coordinates
                        ).filter( and_(
        MediaAssets.id == MediaAssetFeatures.media_asset_id,
        MediaAssetFeatures.feature_type == 'face',
        MediaAssetFeatures.recognition_result.in_( [ 'bad_track', 'bad_face', 'two_face', 'not_face' ] ) ) )

with open( 'output.csv', 'wb' ) as csvfile:
    out = csv.writer( csvfile, quoting=csv.QUOTE_MINIMAL )
    out.writerow( ['media_id', 'track_id', 'image_url', 'detection_result' ] )

    for bad_image in bad_images:
        out.writerow( [ str( bad_image.media_id ), str( bad_image.track_id ), config.ImageServer + bad_image.uri, bad_image.coordinates ] )


