#!/usr/bin/env python

import datetime
import json
import logging
import os
import pdb
from sqlalchemy import and_
import time
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
                      scale: "640:-1", # Passed to ffmpeg -vf scale argument, overrides size
                      size: "640x360", # Currently ignored
                      asset_type: "main",
                      thumbnails : [ {
                        times : [0.5], size: "320x240", label: "poster",
                        format : "png",
                        output_file: { s3_bucket, s3_key } } ]
                     } ] }
                     # If multiple output_files are present, only one need have thumbnails.
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

            # There seems to be a race condition where somehow the OS
            # doesn't present the file to the next command sometimes -
            # give things a few seconds to catch up.
            time.sleep( 3 )

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
                            'message' : "Exception thrown while running qt-faststart for user %s media %s : %s" % ( user_uuid, media_uuid, e ) } ) )
                # Explicitly do nothing upon error in this case.
            
            # Process files into S3
                log.debug( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : "Transcoding and storing the result in S3 for user %s media %s : " % ( user_uuid, media_uuid ) } ) )

            outputs = tutils.transcode_and_store( media_uuid, original_file, outputs, exif )

            orm = vib.db.orm.get_session()
            orm.commit()
            
            # Get the media object to which all our subordinate files relate.
            media = orm.query( Media ).filter( Media.uuid == media_uuid ).first()
            if media is None:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                         'user_uuid' : user_uuid,
                                         'message' : 'Failed to locate database record for media %s, perhaps it has been deleted?' % ( media_uuid ) } ) )
                # Terminate execution permanently, if there is no
                # database record for this we can't possibly proceed.
                return { 'ACTIVITY_ERROR' : True, 'retry' : False }

            if options.get( 'viblio_added_content_type', '' ) != '':
                # This is a viblio generated video, set it's location to Palo Alto
                media.lat = 37.442174
                media.lng = -122.143199
            else:
                media.lat = exif['lat']
                media.lng = exif['lng']

            media.status = 'visible'

            mwfs = MediaWorkflowStages( workflow_stage = self.task_name + 'Complete' )
            media.media_workflow_stages.append( mwfs )

            # Calculate the recording date for video versions.
            if options.get( 'viblio_added_content_type', '' ) != '':
                # This is a viblio generated video, the recording date should be now.
                recording_date = datetime.datetime.now()
            else:
                recording_date = datetime.datetime.utcfromtimestamp( 0 )

            if exif['create_date'] and exif['create_date'] != '' and exif['create_date'] != '0000:00:00 00:00:00':
                try:
                    recording_date = datetime.datetime.strptime( exif['create_date'], '%Y:%m:%d %H:%M:%S' )
                except Exception as e:
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
            original.width = exif.get( 'width', None )
            original.height = exif.get( 'height', None )

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
                    width        = output_exif.get( 'width', None ),
                    height       = output_exif.get( 'height', None ),
                    duration     = output_exif['duration'] )
                media.assets.append( video_asset )

                if output['asset_type'] == 'main' and recording_date != datetime.datetime.utcfromtimestamp( 0 ):
                    try:
                        # Add a Month Year tag to the main media asset.
                        date_string = recording_date.strftime( "%B %Y" )
                        date_tag = MediaAssetFeatures( 
                            feature_type = 'activity',
                            coordinates = date_string
                        )
                        video_asset.media_asset_features.append( date_tag )
                    except Exception as e:
                        log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                                   'user_uuid' : user_uuid,
                                                   'message' : 'Failed to add date tag for video, error was: %s' % ( e ) } ) )

                video_poster = None

                for thumbnail in output.get( 'thumbnails', [] ):
                    thumbnail_uuid = str( uuid.uuid4() )

                    log.info( json.dumps( {
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'asset_type' : thumbnail['label'],
                                'output_uuid' : thumbnail_uuid,
                                'message' : "Creating image database row of uuid %s for user %s, media %s of asset_type %s and uri %s" % ( thumbnail_uuid, user_uuid, media_uuid, thumbnail['label'], thumbnail['output_file']['s3_key'] )
                                } ) )

                    thumbnail_size = thumbnail.get( 'size', "320x240" )
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

                    if thumbnail['label'] == 'poster':
                        video_poster = thumbnail_asset

                for image in output.get( 'images', [] ):
                    image_uuid = str( uuid.uuid4() )

                    log.info( json.dumps( {
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'asset_type' : 'image',
                                'output_uuid' : image_uuid,
                                'message' : "Creating image database row of uuid %s for user %s, media %s of asset_type %s and uri %s" % ( image_uuid, user_uuid, media_uuid, 'image', image['output_file']['s3_key'] )
                                } ) )

                    image_asset = MediaAssets( uuid       = image_uuid,
                                               asset_type = 'image',
                                               mimetype   = 'image/%s' % image.get( 'format', 'png' ),
                                               bytes      = os.path.getsize( image['output_file_fs'] ),
                                               uri        = image['output_file']['s3_key'],
                                               location   = 'us',
                                               timecode   = image['timecode'],
                                               blur_score = image['blur_score'],
                                               face_score = image['face_score'],
                                               cv_metrics = image['cv_metrics'],
                                               view_count = 0 )
                    media.assets.append( image_asset )


            # Determine if we need to create and or add to the special Video summary album.
            if options.get( 'viblio_added_content_type', '' ) == config.viblio_summary_video_type:
                viblio_summary_album = orm.query( Media ).filter( and_( Media.user_id == media.user_id, Media.is_viblio_created == True, Media.title == config.viblio_summary_album_name ) )[:]
            
                if len( viblio_summary_album ) == 0:
                    viblio_summary_album = Media( user_id = media.user_id,
                                                  uuid = str( uuid.uuid4() ),
                                                  media_type = 'original',
                                                  is_album = True,
                                                  title = config.viblio_summary_album_name,
                                                  is_viblio_created = True )
                    orm.add( viblio_summary_album )
                
                    media_album_row = MediaAlbums()
                    orm.add( media_album_row )
                    media.media_albums_media.append( media_album_row )
                    viblio_summary_album.media_albums.append( media_album_row )

                    album_poster = MediaAssets( user_id = media.user_id,
                                                uuid = str( uuid.uuid4() ),
                                                asset_type = 'poster',
                                                mimetype = video_poster.mimetype,
                                                location = video_poster.location,
                                                uri = video_poster.uri, 
                                                width = video_poster.width,
                                                height = video_poster.height )
                    viblio_summary_album.assets.append( album_poster )

                elif len( viblio_summary_album ) == 1:
                    media_album_row = MediaAlbums()
                    orm.add( media_album_row )
                    media.media_albums_media.append( media_album_row )
                    viblio_summary_album[0].media_albums.append( media_album_row )
                else:
                    raise Exception( "ERROR: Found multiple %s albums for user: %s " % ( config.viblio_summary_album_name, media.user_id ) )


            log.info( json.dumps( {
                'media_uuid' : media_uuid,
                'user_uuid' : user_uuid,
                'message' : "Committing rows to database for user %s, media %s" % ( user_uuid, media_uuid )
            } ) )

            #pdb.set_trace()
            orm.commit()
            
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

                for thumbnail in output.get( 'thumbnails', [] ):
                    if 'output_file_fs' in thumbnail:
                        if os.path.exists( thumbnail['output_file_fs'] ):
                            log.debug( json.dumps( {
                                        'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "Deleting temporary file %s for user %s, media %s" % ( thumbnail['output_file_fs'], user_uuid, media_uuid )
                                        } ) )
                            os.remove( thumbnail['output_file_fs'] )

                for image in output.get( 'images', [] ):
                    if 'output_file_fs' in image:
                        if os.path.exists( image['output_file_fs'] ):
                            log.debug( json.dumps( {
                                        'media_uuid' : media_uuid,
                                        'user_uuid' : user_uuid,
                                        'message' : "Deleting temporary file %s for user %s, media %s" % ( image['output_file_fs'], user_uuid, media_uuid )
                                        } ) )
                            os.remove( image['output_file_fs'] )

        except Exception as e:
            log.error( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        'message' : "Exception while cleaning up temporary files for user %s, media %s, error was: %s" % ( user_uuid, media_uuid, e )
                        } ) )
            raise
            
