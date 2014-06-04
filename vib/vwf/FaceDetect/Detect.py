#!/usr/bin/env python

import boto
import commands
import hashlib
import json
import logging
import pprint
import shutil
import os

import vib.rekog.utils
import vib.utils.s3
from vib.vwf.VWorker import VWorker
import vib.vwf.FaceDetect.db_utils as db_utils

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )

class Detect( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'FaceDetect'
    
    def run_task( self, options ):
        '''Perform the face detection logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''
        media_uuid = options['media_uuid']
        user_uuid = options['user_uuid']
        s3_key = options['Transcode']['output_file']['s3_key']
        s3_bucket = options['Transcode']['output_file']['s3_bucket']

        log.info( json.dumps( {  'media_uuid' : media_uuid,
                                 'user_uuid' : user_uuid,
                                 'message' : "Starting Face Detection on media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )

        # Get the media file from S3 for Face Detector
        try:
            working_dir = os.path.abspath( config.faces_dir + media_uuid )
            if not os.path.exists( working_dir ):
                os.makedirs( working_dir )

            short_name = media_uuid + '/' + media_uuid + '.mp4'
            file_name = os.path.abspath( config.faces_dir + short_name )   
            
            vib.utils.s3.download_file( file_name, s3_bucket, s3_key )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Failed to get mp4 file from S3 for media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )
            raise   

        # Run Viblio Face Detection and Tracking Program
        try:
            cmd = 'LD_LIBRARY_PATH=/deploy/vatools/lib /deploy/vatools/bin/viblio_video_analyzer'
            # Neurotechnology face detection
            #opts = ' -f %s --analyzers FaceAnalysis --face_thumbnail_path %s  --filename_prefix %s  --discarded_tracker_frequency 5000 --maximum_concurrent_trackers 10 ' % ( file_name, working_dir, media_uuid )

            # Orbeus face detection
            opts = ' -f %s --face_thumbnail_path %s --filename_prefix %s --analyzers FaceAnalysis --discarded_tracker_frequency 30000 --maximum_concurrent_trackers 7 --face_detector orbeus --orbeus_api_key zdN9xO1srMEFoEsq --orbeus_secret_key bvi5Li9bcQPE3W5S --orbeus_namespace fd_test_2 --orbeus_user_id test ' % ( file_name, working_dir, media_uuid )
            ( status, output ) = commands.getstatusoutput( cmd + opts )
            if status == 0 and ( output.find( "failed (result = -200)" ) == -1 ):
                log.info( json.dumps( {  'media_uuid' : media_uuid,
                                         'user_uuid'  : user_uuid,
                                         'FD command' : cmd + opts,
                                         'message' : "Face Detect Program successful for media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )
            else:
                raise Exception( "Error running %s, message was: %s" % ( cmd + opts, output ) )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'Face Detect Command' : cmd,
                                     'message' : "Face Detect Program failed for media_uuid: %s for user: %s, error: %s" % ( media_uuid, user_uuid, e ) } ) )
            raise

        # Process output json file from Face Detection program
        try:
            file_name = os.path.abspath( working_dir + '/' + media_uuid + '.json' )
            file_handle = open( file_name )
            faces_info = json.load( file_handle )
            file_handle.close()
        except Exception as e:
            log.error( json.dumps( {  'media_uuid' : media_uuid,
                                      'user_uuid' : user_uuid,
                                      'message' : "Output of Face Detect not found or invalid for media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )
            raise

        # Add user_uuid in the return json dict        
        faces_info['user_uuid'] = user_uuid
        faces_info['media_uuid'] = media_uuid

        # Check to see if no faces are returned
        tracks = faces_info['tracks']
        if sum( map( lambda x: 1 if 'faces' in x else 0, tracks ) ) == 0:
            log.info( json.dumps( { 'media_uuid' : media_uuid,
                                    'user_uuid'  : user_uuid,
                                    'message' : "Face Detect didn't find faces for media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )
            try:
                db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
            except Exception as e:
                log.error( json.dumps( { 'media_uuid' : media_uuid,
                                        'user_uuid'  : user_uuid,
                                        'message' : "Failed to update media status, error was: %s" % ( e ) } ) )
                
                return { 'ACTIVITY_ERROR' : True, 'retry' : False }
            
            return faces_info
        else:
            # Process faces
            for track in faces_info['tracks']:
                # Determine the best face by using ReKognition's
                # beauty score.  Default to the first face in the
                # track.
                best_face_score = -1
                best_face = track['faces'][0]
                if len( track['faces'] ) > 1:
                    for face in track['faces']:
                        try:
                            face_file_name = config.faces_dir + face['s3_key']
                            detection = vib.rekog.utils.detect_for_file( face_file_name )
                            max_confidence = -1
                            current_rekog_face = None
                            if 'face_detectin' in detection:
                                for rekog_face in detection['face_detection']:
                                    if rekog_face['confidence'] > max_confidence:
                                        current_rekog_face = rekog_face
                                        max_confidence = rekog_face['confidence']
                            if current_rekog_face is not None and current_rekog_face.get( 'beauty', -1 ) > best_face_score:
                                best_face = face
                                best_face_score = current_rekog_face.get( 'beauty', -1 )
                        except Exception as e:
                            log.warning( json.dumps( { 'media_uuid' : media_uuid,
                                                       'user_uuid' : user_uuid,
                                                       'message' : "Error detecting face beauty score from ReKognition for file %s, error was: %s" % ( face_file_name, e ) } ) )
                            # No further action on failure here

                # Truncate the track to the single best face
                track['faces'] = [ best_face ]
                
                # This logic is from a time when there could be
                # multiple faces - leave it in tact in case we wish to
                # process multiple faces in the future.
                for face in track['faces']:
                    face['s3_bucket'] = s3_bucket
                    face_file_name = config.faces_dir + face['s3_key']
                    file_handle = open( face_file_name )
                    data = file_handle.read()    
                    file_handle.close()
                    md5sum = hashlib.md5(data).hexdigest()
                    face['md5sum'] = md5sum
                    
                    try:
                        vib.utils.s3.upload_file( face_file_name, s3_bucket, face['s3_key'] )
                        db_utils.add_media_asset_face( user_uuid, media_uuid, face['s3_key'], os.path.getsize( face_file_name ), track['track_id'], face )
                        print face
                    except Exception as e:
                        log.error( json.dumps( { 'media_uuid' : media_uuid,
                                                 'user_uuid' : user_uuid,
                                                 'message' : "Failed to store face in s3 for media_uuid: %s for user: %s, error was: %s" % ( media_uuid, user_uuid, e ) } ) )
                        raise

        # Done processing tracks and faces
        # Save the output in S3
        try:
            json_file_name = os.path.abspath( working_dir + '/' + media_uuid + '_faces.json' )
            file_handle = open( json_file_name, 'w' )
            json.dump( faces_info, file_handle )
            file_handle.close()
            json_s3_key = media_uuid + '/' + media_uuid + '_faces.json'
            vib.utils.s3.upload_file( file_name, s3_bucket, json_s3_key )
        except Exception as e:
            log.error( json.dumps( { 'media_uuid' : media_uuid,
                                     'user_uuid' : user_uuid,
                                     'message' : "Uploading faces file failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid ) } ) )
            raise
        
        # Control whether we delete the temporary data.
        if True:
            shutil.rmtree( working_dir )
            
        faces_string = json.dumps( faces_info )

        recognition_input = media_uuid + '/' + media_uuid + '_recognition_input.json'

        vib.utils.s3.upload_string( faces_string, s3_bucket, recognition_input )
        db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )

        return { 
            'user_uuid' : user_uuid,
            'media_uuid' : media_uuid,
            'recognition_input' : {
                's3_bucket' : s3_bucket,
                's3_key' : recognition_input,
                }
            }

