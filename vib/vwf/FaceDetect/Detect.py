#!/usr/bin/env python

import json
import logging
import pprint
import boto
from boto.s3.key import Key
import hashlib


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
        
        s3 = boto.connect_s3( config.awsAccess, config.awsSecret )
        bucket = s3.get_bucket(s3_bucket)
        bucket_contents = Key(bucket)
        
        file_name = config.faces_dir + media_uuid + '/' + media_uuid + '.json'
        file_handle = open(file_name)
        faces_info = json.load(file_handle)
        faces_info['user_uuid'] = user_uuid
        faces_info['media_uuid'] = media_uuid
        for i,track_id in enumerate(faces_info['tracks']):
            track = faces_info['tracks'][i]
            for j,face_id in enumerate(track['faces']):
                face = track['faces'][j]
                face['s3_bucket'] = 'viblio-uploaded-files'    
                file_name = config.faces_dir + face['s3_key']
                file_handle = open(file_name)
                data = file_handle.read()    
                md5sum = hashlib.md5(data).hexdigest()
                face['md5sum'] = md5sum
                try:
                    bucket_contents.key = face['s3_key']
                    byte_size = bucket_contents.set_contents_from_filename(filename=file_name)
                    if bucket_contents.md5 != md5sum:
                        print ('md5 match failed')
                        raise
                    db_utils.add_media_asset_face(user_uuid, media_uuid, face['s3_key'], byte_size, track_id['track_id'], face)
                except Exception as e:
                    print ( 'Failed to upload to s3: %s' % str( e ) )
                    raise
                print face
        json_string = json.dumps(faces_info)
        return(json_string)
        
        
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


