#!/usr/bin/env python

import datetime
from PIL import Image
import os
import json
import pprint
import requests
from sqlalchemy import and_
from StringIO import StringIO

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

orm = vib.db.orm.get_session()

from_when = datetime.datetime.utcnow() - datetime.timedelta( days=10 )

faces = orm.query( Media.filename, 
                   MediaAssets.uri,
                   MediaAssetFeatures.id,
                   MediaAssetFeatures.media_id,
                   MediaAssetFeatures.track_id,
                   MediaAssetFeatures.coordinates
                   ).filter( and_(
        Media.id == MediaAssets.media_id,
        Media.id == MediaAssetFeatures.media_id,
        MediaAssets.id == MediaAssetFeatures.media_asset_id,
        MediaAssetFeatures.feature_type == 'face',
        MediaAssetFeatures.recognition_result == None,
        MediaAssetFeatures.created_date >= from_when ) ) 

outdir = '/wintmp/faces/'

if not os.path.exists( outdir ):
    os.makedirs( outdir )

seen = {}

def get_face( f ):
        try:
            result = requests.get( config.ImageServer + f.uri )
            image = Image.open( StringIO( result.content ) )
            filename = "%s%s_%s_%s.jpg" % ( outdir, f.media_id, f.track_id, f.id )
            image.save( filename )
            outfile = open( "%s%s_%s_%s.json" % ( outdir, f.media_id, f.track_id, f.id ), 'w' )
            pp = pprint.PrettyPrinter( indent=4, stream=outfile )
            pp.pprint( json.loads( f.coordinates ) )
            outfile.close()
        except:
            pass


for f in faces:
    if f.filename not in seen:
        print "Starting work on", f.filename
        seen[f.filename] = { f.media_id : True }
        get_face( f )
    elif f.media_id in seen[ f.filename ]:
        print "Continuing to work on", f.filename
        get_face( f )
    else:
        print "Skipping duplicate of", f.filename

