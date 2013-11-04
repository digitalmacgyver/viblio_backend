#!/usr/bin/env python

import hmac
import json
import logging
import requests

from vib.vwf.VWorker import VWorker

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

log = logging.getLogger( __name__ )

class Notify( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'Transcode'
    
    def run_task( self, options ):
        '''Transcode a video.  Input options are:
        { media_uuid, user_uuid, input_file : { s3_bucket, s3_key },
          outputs : [ { output_file : { s3_bucket, s3_key},
                      format : "mp4", 
                      max_video_bitrate: 1500,
                      audio_bitrate : 160,
                      size: "640x360",
                      thumbnails : [ {
                        times : [0.5], size: "320x180", label: "poster",
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

            original_exif = tutils.get_exif( media_uuid, original_file )

            try:
                tutils.move_atom( media_uuid, original_file )
            except:
                pass
            
            # Process files into S3
            for output in outputs:
                tutils.transcode( original_file, outputs, original_exif )

            # Store stuff in DB

            # Clean up

            
        except Exception as e:
            # DEBUG go something
            pass


'''
        # Generate _exif.json and load it into self.data['exif']
        log.info( 'Getting exif data from file %s and storing it to %s' % ( files['exif']['ifile'], files['exif']['ofile'] ) )
        try:
            self.data['exif'] = helpers.get_exif( files['exif'], log, self.data )
            log.info( 'EXIF data extracted: ' + str( self.data['exif'] ) )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Error during exif extraction: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise


        # Give the input file an extension.
        log.info( 'Renaming input file %s with lower cased file extension based on uploader information' % files['main']['ifile'] )
        try:
            new_filename = helpers.rename_upload_with_extension( files['main'], log, self.data )
            log.info( 'Renamed input file is: ' + new_filename )
            files['main']['ifile'] = new_filename
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Could not rename input file, error was: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        # Extract the mimetype and store it in self.data['mimetype']
        log.info( 'Getting mime type of input video.' )
        try:
            self.data['mimetype'] = str( mimetypes.guess_type( files['main']['ifile'] )[0] )
            log.info( 'Mime type was ' + self.data['mimetype'] )
        except Exception as e:
            self.__safe_log( self.popeye_log.exception, 'Failed to get mime type, error was: ' + str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise

        try: 
            # Transcode into mp4 and rotate as needed.
            log.info( 'Transcode %s to %s' % ( files['main']['ifile'], files['main']['ofile'] ) )
            log.info( 'Before transcoding file %s is %s bytes.' % ( files['main']['ifile'], str( os.path.getsize( files['main']['ifile'] ) ) ) )
            video_processing.transcode_main( files['main'], log, self.data )

            log.info( 'Transcoded mime type is ' + self.data['mimetype'] )
            log.info( 'After transcoding file %s is %s bytes.' % ( files['main']['ofile'], str( os.path.getsize( files['main']['ofile'] ) ) ) )

            #self.mp_log( '030_transcode_mp4_completed' )

            # Move the atom to the front of the file.
            log.info( 'Move atom for: ' + files['main']['ofile'] )
            video_processing.move_atom( files['main'], log, self.data )
            
            # Generate _exif.json for transcoded input
            log.info( 'Getting exif data from file %s and storing it to %s' % ( files['transcoded_exif']['ifile'], files['transcoded_exif']['ofile'] ) )
            try:
                self.data['transcoded_exif'] = helpers.get_exif( files['transcoded_exif'], log, self.data )
                log.info( 'Transcoded EXIF data extracted: ' + str( self.data['transcoded_exif'] ) )
            except Exception as e:
                self.__safe_log( self.popeye_log.exception, 'Error during exif extraction: ' + str( e ) )
                self.handle_errors()
                self.__release_lock()
                if self.popeye_logging_handler:
                    self.popeye_log.removeHandler( self.popeye_logging_handler )
                    self.popeye_logging_handler = None
                raise

           # Create a poster.
            log.info( 'Generate poster from %s to %s' % ( files['poster']['ifile'], files['poster']['ofile'] ) )
            video_processing.generate_poster( files['poster'], log, self.data )
            
            #self.mp_log( '050_poster_completed' )

            # Create a thumbnail.
            log.info( 'Generate thumbnail from %s to %s' % ( files['thumbnail']['ifile'], files['thumbnail']['ofile'] ) )
            video_processing.generate_thumbnail( files['thumbnail'], log, self.data )

            self.mp_log( '060_thumbnail_completed' )

        except Exception as e:
            self.__safe_log( self.popeye_log.exception, str( e ) )
            self.handle_errors()
            self.__release_lock()
            if self.popeye_logging_handler:
                self.popeye_log.removeHandler( self.popeye_logging_handler )
                self.popeye_logging_handler = None
            raise




        except Exception as e:
            log.error( json.dumps( {
                        'media_uuid' : media_uuid,
                        'user_uuid' : user_uuid,
                        } ) )
            # Hopefully some blip, fail with retry status.
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }

'''
