#!/usr/bin/env python

import datetime
import json
import logging
import os
import pdb
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
          original_uuid,
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
                        'message' : "Starting transcode for user %s media %s" % ( user_uuid, media_uuid )
                    } ) )

            # Download to our local disk.
            original_file = config.transcode_dir + "/"  + media_uuid
            log.debug( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Downloading original file from s3 for user %s media %s" % ( user_uuid, media_uuid )
                    } ) )

            s3.download_file( original_file, input_file['s3_bucket'], input_file['s3_key'] )

            log.debug( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Generating exif for original file for user %s media %s" % ( user_uuid, media_uuid )
                    } ) )
            exif = tutils.get_exif( media_uuid, original_file )

            try:
                log.debug( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Running qt-faststart for user %s media %s" % ( user_uuid, media_uuid )
                    } ) )
                tutils.move_atom( media_uuid, original_file )
            except Exception as e:
                log.warning( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Exception thrown while running qt-faststart for user %s media %s : %s" % ( user_uuid, media_uuid, e )
                    } ) )
                # Explicitly do nothing upon error in this case.
            
            # Process files into S3
            log.debug( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Transcoding and storing the result in S3 for user %s media %s : " % ( user_uuid, media_uuid )
                        } ) )

            #pdb.set_trace()
            self.heartbeat()
            outputs = tutils.transcode_and_store( media_uuid, original_file, outputs, exif )
            self.heartbeat()

            orm = vib.db.orm.get_session()

            # Get the media object to which all our subordinate files relate.
            media = orm.query( Media ).filter( Media.uuid == media_uuid ).first()
            if media is None:
                log.error( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : 'Failed to locate database record for media %s, perhaps it has been deleted?' % ( media_uuid ) } ) )
                # Terminate execution permanently, if there is no
                # database record for this we can't possibly proceed.
                return { 'ACTIVITY_ERROR' : True, 'retry' : False }

            media.lat = exif['lat']
            media.lng = exif['lng']
            media.status = 'visible'

            mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
            media.media_workflow_stages.append( mwfs )

            # Calculate the recording date for video versions.
            recording_date = datetime.datetime.utcfromtimestamp( 0 )
            if exif['create_date'] and exif['create_date'] != '' and exif['create_date'] != '0000:00:00 00:00:00':
                recording_date = exif['create_date']
            log.debug( 'Setting recording date to ' + str( recording_date ) )
            log.debug( 'Exif data for create was ' + exif['create_date'] )    
            media.recording_date = recording_date

            original = orm.query( MediaAssets ).filter( MediaAssets.uuid == options['original_uuid'] ).first()
            if original is None:
                log.error( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : 'Failed to locate database record for original media asset %s, perhaps it has been deleted?' % ( media_uuid ) } ) )
                # Terminate execution permanently, if there is no
                # database record for this we can't possibly proceed.
                return { 'ACTIVITY_ERROR' : True, 'retry' : False }

            original.mimetype = 'video/%s' % exif.get( 'format', 'mp4' )

            # We will return to the next stage the key/bucket of the
            # "main" asset_type.
            return_bucket = None
            return_key = None

            for output in outputs:
                output_uuid = str( uuid.uuid4() )

                output_exif = tutils.get_exif( media_uuid, output['output_file_fs'] )

                log.info( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'asset_type' : output['asset_type'],
                            'output_uuid' : output_uuid,
                            'message' : "Creating video database row of uuid %s for user %s, media %s of asset_type %s and uri %s" % ( output_uuid, user_uuid, media_uuid, output['asset_type'], output['output_file']['s3_key'] )
                    } ) )

                if output['asset_type'] == 'main':
                    return_bucket = output['output_file']['s3_bucket']
                    return_key = output['output_file']['s3_key']

                video_asset = MediaAssets( 
                    uuid         = output_uuid,
                    asset_type   = output['asset_type'],
                    mimetype     = 'video/%s' % exif.get( 'format', 'mp4' ),
                    metadata_uri = options['metadata_uri'],
                    bytes        = os.path.getsize( output['output_file_fs'] ),
                    uri          = output['output_file']['s3_key'],
                    location     = 'us',
                    view_count   = 0,
                    duration     = output_exif['duration'] )
                media.assets.append( video_asset )

                for thumbnail in output['thumbnails']:
                    thumbnail_uuid = str( uuid.uuid4() )

                    log.info( json.dumps( {
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'asset_type' : thumbnail['label'],
                                'output_uuid' : thumbnail_uuid,
                                'message' : "Creating image database row of uuid %s for user %s, media %s of asset_type %s and uri %s" % ( thumbnail_uuid, user_uuid, media_uuid, thumbnail['label'], thumbnail['output_file']['s3_key'] )
                                } ) )

                    thumbnail_size = thumbnail.get( 'size', "320x180" )
                    thumbnail_x, thumbnail_y = thumbnail_size.split( 'x' )
                    thumbnail_asset = MediaAssets( uuid       = thumbnail_uuid,
                                                   asset_type = thumbnail['label'],
                                                   mimetype   = 'image/%s' % thumbnail.get( 'format', 'png' ),
                                                   bytes      = os.path.getsize( thumbnail['output_file_fs'] ),
                                                   width      = int( thumbnail_x ), 
                                                   height     = int( thumbnail_y ),
                                                   uri        = thumbnail['output_file']['s3_key'],
                                                   location   = 'us',
                                                   view_count = 0 )
                    media.assets.append( thumbnail_asset )

            log.info( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Committing rows to database for user %s, media %s" % ( user_uuid, media_uuid )
                        } ) )

            #pdb.set_trace()
            self.heartbeat()
            orm.commit()
            self.heartbeat()

            self.cleanup_files( media_uuid, user_uuid, original_file, outputs )
            
            return_value = { 
                'media_uuid' : media_uuid,
                'user_uuid' : user_uuid,
                'output_file' : {
                    's3_bucket' : return_bucket,
                    's3_key' : return_key
                    }
                }

            return return_value

        except Exception as e:
            log.error( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Exception while transcoding video for user %s, media %s, error was: %s" % ( user_uuid, media_uuid, e )
                        } ) )

            self.cleanup_files( media_uuid, user_uuid, original_file, outputs )
            raise

    def cleanup_files( self, media_uuid, user_uuid, original_file, outputs ):
        try:
            # Delete the original file
            if os.path.exists( original_file ):
                log.debug( json.dumps( {
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "Deleting temporary file %s for user %s, media %s" % ( original_file, user_uuid, media_uuid )
                            } ) )
                os.remove( original_file )

                exif_file = os.path.splitext( original_file )[0] + '_exif.json'
                
                if os.path.exists( exif_file ):
                    log.debug( json.dumps( {
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'message' : "Deleting temporary file %s for user %s, media %s" % ( exif_file, user_uuid, media_uuid )
                                } ) )
                    os.remove( exif_file )
                    
            # Delete file files created and stored in the outputs data
            # structure.
            for output in outputs:
                if 'output_file_fs' in output:
                    if os.path.exists( output['output_file_fs'] ):
                        log.debug( json.dumps( {
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "Deleting temporary file %s for user %s, media %s" % ( output['output_file_fs'], user_uuid, media_uuid )
                                } ) )
                        os.remove( output['output_file_fs'] )

                        exif_file = os.path.splitext( output['output_file_fs'] )[0] + '_exif.json'
                
                        if os.path.exists( exif_file ):
                            log.debug( json.dumps( {
                                        'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "Deleting temporary file %s for user %s, media %s" % ( output['output_file_fs'], user_uuid, media_uuid )
                                        } ) )
                            os.remove( exif_file )

                for thumbnail in output['thumbnails']:
                    if 'output_file_fs' in thumbnail:
                        if os.path.exists( thumbnail['output_file_fs'] ):
                            log.debug( json.dumps( {
                                        'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "Deleting temporary file %s for user %s, media %s" % ( thumbnail['output_file_fs'], user_uuid, media_uuid )
                                        } ) )
                            os.remove( thumbnail['output_file_fs'] )

        except Exception as e:
            log.error( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Exception while cleaning up temporary files for user %s, media %s, error was: %s" % ( user_uuid, media_uuid, e )
                        } ) )
            raise
            
