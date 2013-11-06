#!/usr/bin/env python

import datetime
import json
import logging
import os
import uuid

from vib.vwf.VWorker import VWorker

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

import vib.vwf.Transcode.transcode_utils as tutils

log = logging.getLogger( __name__ )

class Transcode( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'Transcode'
    
    def run_task( self, options ):
        '''Transcode a video.  Input options are:
        { media_uuid, user_uuid, input_file : { s3_bucket, s3_key },
          metadata_uri, 
          outputs : [ { output_file : { s3_bucket, s3_key},
                      format : "mp4", 
                      max_video_bitrate: 1500,
                      audio_bitrate : 160,
                      size: "640x360",
                      asset_type: "main",
                      thumbnails : [ {
                        times : [0.5], size: "320x180", label: "poster",
                        format : "png",
                        output_file: { s3_bucket, s3_key } } ]
                     } ] }
        '''
        try:
            media_uuid = options['media_uuid']
            user_uuid = options['user_uuid']
            input_file = options['input_file']
            outputs = options['outputs']

            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                    } ) )

            # LOGIC:
            # 1. Download file
            # 2. Generate exif
            # 3. For each: transcode / genereate
            # 4. Update original media with recording date, lat/lng, 

            # Download to our local disk.
            original_file = config.transcode_dir + "/"  + media_uuid
            s3.download_file( original_file, input_file['s3_bucket'], input_file['s3_key'] )

            exif = tutils.get_exif( media_uuid, original_file )

            try:
                tutils.move_atom( media_uuid, original_file )
            except:
                pass
            
            # Process files into S3
            outputs = tutils.transcode_and_store( media_uuid, original_file, outputs, exif )

            orm = vib.db.orm.get_session()

            log.info( 'Getting the current user from the database for uid: %s' % user_uuid )

            media = orm.query( Media ).filter( Media.uuid == media_uuid ).one()

            media.lat = exif['lat']
            media.lng = exif['lng']

            recording_date = datetime.datetime.now()
            if exif['create_date'] and exif['create_date'] != '' and exif['create_date'] != '0000:00:00 00:00:00':
                recording_date = exif['create_date']
            log.debug( 'Setting recording date to ' + str( recording_date ) )
            log.debug( 'Exif data for create was ' + exif['create_date'] )    
            media.recording_date = recording_date

            return_bucket = None
            return_key = None

            for output in outputs:
                # Main media_asset
                log.info( 'Generating row for %s media_asset' % output['asset_type'] )
                if output['asset_type'] == 'main':
                    return_bucket = output['output_file']['s3_bucket']
                    return_key = output['output_file']['s3_key']
                video_asset = MediaAssets( 
                    uuid         = str( uuid.uuid4() ),
                    asset_type   = output['asset_type'],
                    mimetype     = 'video/%s' % exif.get( 'format', 'mp4' ),
                    # DEBUG - we don't have this here, it is in Brewtus?!?!?
                    # DEBUG - does this even make sense for any asset type other than main?
                    metadata_uri = options['metadata_uri'],
                    bytes        = os.path.getsize( output['output_file_fs'] ),
                    uri          = output['output_file']['s3_key'],
                    location     = 'us',
                    view_count   = 0 )
                media.assets.append( video_asset )

                for thumbnail in output['thumbnails']:
                    # Thumbnail media_asset
                    log.info( 'Generating row for thumbnail media_asset' )
                    thumbnail_size = thumbnail.get( 'size', "320x180" )
                    thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )
                    thumbnail_asset = MediaAssets( uuid       = str(uuid.uuid4()),
                                                   asset_type = thumbnail['label'],
                                                   mimetype   = 'image/%s' % thumbnail.get( 'format', 'png' ),
                                                   bytes      = os.path.getsize( thumbnail['output_file_fs'] ),
                                                   width      = int( thumbnail_x ), 
                                                   height     = int( thumbnail_y ),
                                                   uri        = thumbnail['output_file']['s3_key'],
                                                   location   = 'us',
                                                   view_count = 0 )
                    media.assets.append( thumbnail_asset )

            orm.commit()

            # DEBUG - delete everything.
            
            return { 
                'media_uuid' : media_uuid,
                'user_uuid' : user_uuid,
                'output_file' : {
                    's3_bucket' : return_bucket,
                    's3_key' : return_key
                    }
                }

        except Exception as e:
            log.exception( "OOps: %s" % e )
            raise

