import boto.sqs.connection
from boto.sqs.connection import Message
from boto.sqs.message import RawMessage
import json
import logging
from logging import handlers
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.cv.FaceRecognition.api as rec

log = logging.getLogger( 'vib.cv.FaceRecognition' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'fb: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def delete_contact( user_id, contact_id ):
    '''Deletes a contact and all recognition information about that
    contact.'''
    try:
        log.info( json.dumps( { 'user_id' : user_id,
                                'contact_id' : contact_id, 
                                'message' : "Deleting recognition contact_id %s for user_id %s" % ( contact_id, user_id ) } ) )
        rec.delete_contact( user_id, contact_id )
    except Exception as e:
        log.error( json.dumps( { 'user_id' : user_id,
                                 'contact_id' : contact_id, 
                                 'message' : "Failed to delete contact: %e" % ( e ) } ) )
        raise

def delete_faces_for_contact( user_id, contact_id, media_asset_feature_ids ):
    '''Deletes a given set of faces from a contact from the
    recognition system.'''
    try:
        if len( media_asset_feature_ids ) > 0:
            log.info( json.dumps( { 'user_id' : user_id,
                                    'contact_id' : contact_id, 
                                    'message' : "Deleting %s faces from contact_id %s for user_id %s" % ( len( media_asset_feature_ids ), contact_id, user_id ) } ) )
            
            all_faces = rec.get_faces( user_id, contact_id )

            delete_faces = []

            for face in all_faces:
                if face['face_id'] in media_asset_feature_ids:
                    delete_faces.append( face )

            if len( delete_faces ):
                result = rec.delete_faces( user_id, contact_id, delete_faces )

                if len( result['deleted'] ) != len( delete_faces ):
                    log.warning( json.dumps( { 'user_id' : user_id,
                                               'contact_id' : contact_id, 
                                               'message' : "Attempted to delete %s faces, successfully deleted %s faces, however %s were not found in the recognition system, and %s had errors on attempted deletion." % ( len( delete_faces ), len( result['deleted'] ), len( result['unchanged'] ), len( result['error'] ) ) } ) )

        return
                
    except Exception as e:
        log.error( json.dumps( { 'user_id' : user_id,
                                 'contact_id' : contact_id, 
                                 'message' : "Failed to delete faces for contact: %e" % ( e ) } ) )
        raise

def move_faces( user_id, old_contact_id, new_contact_id, media_asset_feature_ids ):
    '''Moves a set of faces from an old contact to a new one.'''
    try:
        if len( media_asset_feature_ids ) > 0:
            log.info( json.dumps( { 'user_id' : user_id,
                                    'message' : "Moving %s faces from contact_id %s to contact_id %s for user_id %s" % ( len( media_asset_feature_ids ), old_contact_id, new_contact_id, user_id ) } ) )
            
            all_faces = rec.get_faces( user_id, old_contact_id )
            new_faces = []
            delete_faces = []

            for face in all_faces:
                if face['face_id'] in media_asset_feature_ids:
                    new_faces.append( {
                            'user_id'     : face['user_id'],
                            'contact_id'  : new_contact_id,
                            'face_id'     : face['face_id'],
                            'face_url'    : face['face_url'],
                            'external_id' : face['external_id'],
                            'score'       : face['score']
                            } )
                    delete_faces.append( face )

            if len( new_faces ):
                add_new = rec.add_faces( user_id, new_contact_id, new_faces )

                if len( add_new['added'] ) != len( new_faces ):
                    log.warning( json.dumps( { 'user_id' : user_id,
                                               'message' : "Attempted to add %s faces, successfully added %s faces, however %s were already found in the recognition system, and %s had errors on attempted addition." % ( len( new_faces ), len( add_new['added'] ), len( add_new['unchanged'] ), len( add_new['error'] ) ) } ) )

            if len( delete_faces ):
                delete = rec.delete_faces( user_id, old_contact_id, delete_faces )

                if len( delete['deleted'] ) != len( delete_faces ):
                    log.warning( json.dumps( { 'user_id' : user_id,
                                               'message' : "Attempted to delete %s faces, successfully deleted %s faces, however %s were not found in the recognition system, and %s had errors on attempted deletion." % ( len( delete_faces ), len( delete['deleted'] ), len( delete['unchanged'] ), len( delete['error'] ) ) } ) )
                      
        return
    except Exception as e:
        log.error( json.dumps( { 'user_id' : user_id,
                                 'message' : "Failed to move faces: %e" % ( e ) } ) )
        raise

def __get_sqs():
    return boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

sqs = __get_sqs().get_queue( config.recog_queue )
sqs.set_message_class( RawMessage )

def run():
    try:
        message = None
        message = sqs.read( wait_time_seconds = 20 )

        if message == None:
            time.sleep( 10 )
            return True

        body = message.get_body()

        try:
            log.info( json.dumps( { 'message' : "Reviewing candidate message with body was: %s" % body } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting body to string, error was: %s" % e } ) )

        options = json.loads( body )

        try:
            log.debug( json.dumps( { 'message' : "Options are %s: " % options } ) )
        except Exception as e:
            log.debug( json.dumps( { 'message' : "Error converting options to string: %e" % e } ) )

        action = options['action']
        user_id = int( options['user_id'] )
        media_asset_feature_ids = [ int( x ) for x in options['media_asset_feature_ids'] ]
        contact_id = None
        new_contact_id = None
        old_contact_id = None
        delete_old_contact = False

        if action == 'move_faces':
            new_contact_id = int( options['new_contact'] )
            old_contact_id = int( options['old_contact'] )
            delete_old_contact = options.get( 'delete_old_contact', False )
        else:
            contact_id = int( options['contact_id'] )

        if action == 'delete_contact':
            delete_contact( user_id, contact_id )
        elif action == 'delete_faces_for_contact':
            delete_faces_for_contact( user_id, contact_id, media_asset_feature_ids )
        elif action == 'move_faces':
            move_faces( user_id, old_contact_id, new_contact_id, media_asset_feature_ids )
            if delete_old_contact:
                delete_contact( user_id, old_contact_id )
        else:
            log.error( json.dumps( { "Error, unknown action: %s" % ( action ) } ) )

        sqs.delete_message( message )
        return True

    except Exception as e:
        log.error( json.dumps( { 'message' : 'Exception was %s' % ( e ) } ) )
        raise
