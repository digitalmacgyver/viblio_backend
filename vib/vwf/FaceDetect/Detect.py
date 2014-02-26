#!/usr/bin/env python

import boto
import hashlib
import json
import logging
import pprint
import shutil
import os

from boto.s3.key import Key
from vib.vwf.VWorker import VWorker
import vib.vwf.FaceDetect.db_utils as db_utils
import vib.utils.s3

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

        log.info( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Starting Face Detection on media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
        # Open connection to S3
        try:
            s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
            bucket = s3.get_bucket(s3_bucket)
            bucket_contents = Key(bucket)
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Connection to S3 failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        # Get the media file from S3 for Face Detector
        try:
            working_dir = os.path.abspath( config.faces_dir + media_uuid )
            if not os.path.exists(working_dir):
                os.makedirs(working_dir)

            short_name = media_uuid + '/' + media_uuid + '.mp4'
            file_name = os.path.abspath( config.faces_dir + short_name )   
            key = bucket.get_key( s3_key )
            key.get_contents_to_filename( file_name )

        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Failed to get mp4 file from S3 for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise   
        # Run Viblio Face Detection and Tracking Program
        try:
            cmd = 'LD_LIBRARY_PATH=/deploy/vatools/lib /deploy/vatools/bin/viblio_video_analyzer'
            opts = ' -f %s --analyzers FaceAnalysis --face_thumbnail_path %s  --filename_prefix %s' %(file_name, working_dir, media_uuid)
            os.system( cmd + opts )
            log.info( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid'  : user_uuid,
                    'FD command' : cmd + opts,
                    'message' : "Face Detect Program successful for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'Face Detect Command' : cmd,
                    'message' : "Face Detect Program failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        # Process output json file from Face Detection program
        try:
            file_name = os.path.abspath( working_dir + '/' + media_uuid + '.json')
            file_handle = open(file_name)
            faces_info = json.load(file_handle)
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Output of Face Detect not found or invalid for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        # Add user_uuid in the return json dict        
        faces_info['user_uuid'] = user_uuid
        faces_info['media_uuid'] = media_uuid
        # Check to see if no faces are returned
        tracks = faces_info['tracks']
        if str(tracks).find('faces') <= 0:
            log.info( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid'  : user_uuid,
                    'message' : "Face Detect didn't find faces for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            self.heartbeat()
            db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
            self.heartbeat()
            return faces_info
        else:
            # Process faces
            for i,track_id in enumerate(faces_info['tracks']):
                track = faces_info['tracks'][i]
                for j,face_id in enumerate(track['faces']):
                    face = track['faces'][j]
                    face['s3_bucket'] = s3_bucket
                    file_name = config.faces_dir + face['s3_key']
                    file_handle = open(file_name)
                    data = file_handle.read()    
                    md5sum = hashlib.md5(data).hexdigest()
                    face['md5sum'] = md5sum
                    try:
                        self.heartbeat()
                        bucket_contents.key = face['s3_key']
                        byte_size = bucket_contents.set_contents_from_filename(filename=file_name)
                        self.heartbeat()
                        if bucket_contents.md5 != md5sum:
                            log.error( json.dumps( { 
                                    'media_uuid' : media_uuid,
                                    'user_uuid' : user_uuid,
                                    'message' : "MD5 mismatch for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                                    } ) )
                            raise
                        self.heartbeat()
                        db_utils.add_media_asset_face(user_uuid, media_uuid, face['s3_key'], byte_size, track_id['track_id'], face)
                        self.heartbeat()
                    except Exception as e:
                        log.error( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'message' : "MD5 mismatch for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                                } ) )
                        raise Exception( "Md5 mismatch" )
                    print face
        # Done processing tracks and faces
        # Save the output in S3
        try:
            file_name = os.path.abspath( working_dir + '/' + media_uuid + '_faces.json')
            file_handle = open(file_name, 'w')
            json.dump( faces_info, file_handle )
            s3_key = media_uuid + '/' + media_uuid + '_faces.json'
            self.heartbeat()
            bucket_contents.key = s3_key
            byte_size = bucket_contents.set_contents_from_filename(filename=file_name)
            self.heartbeat()
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Uploading faces file failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        
        # Control whether we delete the temporary data.
        if True:
            shutil.rmtree(working_dir)
            
        faces_string = json.dumps(faces_info)

        

        recognition_input = media_uuid + '/' + media_uuid + '_recognition_input.json'

        self.heartbeat()
        vib.utils.s3.upload_string( faces_string, s3_bucket, recognition_input )
        db_utils.update_media_status( media_uuid, self.task_name + 'Complete' )
        self.heartbeat()

        return { 
            'user_uuid' : user_uuid,
            'media_uuid' : media_uuid,
            'recognition_input' : {
                's3_bucket' : s3_bucket,
                's3_key' : recognition_input,
                }
            }

    def run_cleanup_files(self, options):
        media_uuid = options['media_uuid']
        user_uuid = options['user_uuid']
        log.info( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Cleaning up files for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
        # Get the media file from S3 for Face Detector
        try:
            working_dir = os.path.abspath( config.faces_dir + media_uuid )
            json_file_name = os.path.abspath( working_dir + '/' + media_uuid + '.json')
            if os.path.isfile(json_file_name):
                file_handle = open(json_file_name)
                faces_info = json.load(file_handle)
                tracks = faces_info['tracks']
                if str(tracks).find('faces') <= 0:
                    if os.path.isfile(json_file_name):
                        os.remove(json_file_name)
                        os.rmdir(working_dir)
                    return
                else:
                    # Process faces
                    for i,track_id in enumerate(faces_info['tracks']):
                        track = faces_info['tracks'][i]
                        for j,face_id in enumerate(track['faces']):
                            face = track['faces'][j]
                            file_name = config.faces_dir + face['s3_key']
                            if os.path.isfile(file_name):
                                os.remove(file_name)
                    if os.path.isfile(json_file_name):
                        os.remove(json_file_name)
                        os.rmdir(working_dir)
                    return
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "File cleanup failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise Exception( "Cleanup failed" )
        
