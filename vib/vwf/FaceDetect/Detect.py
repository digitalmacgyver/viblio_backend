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
        s3_bucket = options['s3_bucket']

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
                os.mkdir(working_dir)
            s3_key = media_uuid + '/' + media_uuid + '.mp4'
            file_name = os.path.abspath( config.faces_dir + s3_key )           
            key = bucket.get_key(s3_key)
            key.get_contents_to_filename(file_name)
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
        faces_info['user_uuid'] = user_uuid
        faces_info['media_uuid'] = media_uuid
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
                    bucket_contents.key = face['s3_key']
                    byte_size = bucket_contents.set_contents_from_filename(filename=file_name)
                    if bucket_contents.md5 != md5sum:
                        log.error( json.dumps( { 
                                'media_uuid' : media_uuid,
                                'user_uuid' : user_uuid,
                                'message' : "MD5 mismatch for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                                } ) )
                        raise
                    db_utils.add_media_asset_face(user_uuid, media_uuid, face['s3_key'], byte_size, track_id['track_id'], face)
                except Exception as e:
                    log.error( json.dumps( { 
                            'media_uuid' : media_uuid,
                            'user_uuid' : user_uuid,
                            'message' : "MD5 mismatch for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                            } ) )
                    raise
                print face
        # Done processing tracks and faces
        # Save the output in S3
        try:
            file_name = os.path.abspath( working_dir + '/' + media_uuid + '_faces.json')
            file_handle = open(file_name, 'w')
            json.dump( faces_info, file_handle )
            s3_key = media_uuid + '/' + media_uuid + '_faces.json'
            bucket_contents.key = face['s3_key']
            byte_size = bucket_contents.set_contents_from_filename(filename=file_name)
        except Exception as e:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Uploading faces file failed for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        
        # Control whether we delete the temp data.
        if True:
            shutil.rmtree(working_dir)
            
        faces_string = json.dumps(faces_info)
        # Check to make sure returned json string is smaller than 32K characters
        if len(faces_string) > 32000:
            log.error( json.dumps( { 
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : "Face Detect output too large for media_uuid: %s for user: %s" % ( media_uuid, user_uuid )
                    } ) )
            raise
        else:
            return faces_info
        
        
        # Logging is set up to log to syslog in the parent VWorker class.
        # 
        # In turn syslog is set up to go to our Loggly cloud logging
        # server on our servers.
        #
        # Loggly likes JSON formatted log messages for parsability.
        #
        # Example of how to log, send in a JSON to the logger.  Always
        # include media_uuid and user_uuid if they are in scope /
        # sensible, and always include a message.  Include other keys
        # you'd like to search on when dealing with that message
        # (e.g. s3_key, track_id, whatever)
        log.info( json.dumps( {
                    'media_uuid' : media_uuid,
                    'user_uuid' : user_uuid,
                    'message' : 'A log message from the face detector.'
                    } ) )


        print "Face detection inputs are:"
        pp = pprint.PrettyPrinter( indent=4 )
        pp.pprint( options )
        print "Doing face detection stuff!"

        recoverable_error = False
        catastrophic_error = False
        if catastrophic_error:
            return { 'ACTIVITY_ERROR' : True, 'retry' : False }
        elif recoverable_error:
            return { 'ACTIVITY_ERROR' : True, 'retry' : True }
        else: 
            # As a placeholder, just pass our input back out.
            return options


