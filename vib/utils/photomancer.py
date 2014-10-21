#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.message import RawMessage
import json
from sqlalchemy import and_, not_

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()


# Start a photo processing job for each video that is missing photos.

from vib.db.models import *
import vib.db.orm

orm = vib.db.orm.get_session()

no_image_videos = orm.query( Media ).filter( and_( Media.media_type == 'original', Media.is_album != 1, Media.status.in_( [ 'visible', 'complete' ] ), ~Media.assets.any( MediaAssets.asset_type == 'image' ) ) )

def get_connection():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

conn = get_connection()

q = conn.get_queue( config.photo_finder_queue )
for niv in no_image_videos:
    print "Working on:", niv.uuid
    m = RawMessage()
    m.set_body( json.dumps( { 'media_uuid' : niv.uuid } ) )
    status = q.write( m )
    print "\t", status



