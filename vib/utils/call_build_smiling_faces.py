#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.connection import Message
import json
import logging
from optparse import OptionParser
import sys
import sqlalchemy
from sqlalchemy import and_, distinct, func

import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'call_build_smiling_faces: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def call_build_smiling_faces( min_videos = 5, user_uuid = None, max_retries = 4, force = False ):
    log.info( json.dumps( { 'message' : 'Processing with min_videos: %s, user_uuid: %s, max_retries: %s force: %s' % ( min_videos, user_uuid, max_retries, force ) } ) )
    
    orm = vib.db.orm.get_session()
    orm.commit()

    user_id = None
    if user_uuid is not None:
        user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()
        user_id = user.id
        
    build_users = [];

    if force:
        # Get all eligible users regardless of status in viblio_added_content
        all_users = None
        if user_uuid is None:
            all_users = orm.query( MediaAssetFeatures.user_id, func.count( distinct( MediaAssetFeatures.media_id ) ) ).filter( MediaAssetFeatures.feature_type == 'face' )
        else:
            all_users = orm.query( MediaAssetFeatures.user_id, func.count( distinct( MediaAssetFeatures.media_id ) ) ).filter( and_( MediaAssetFeatures.user_id == user_id, MediaAssetFeatures.feature_type == 'face' ) )

        for user in all_users:
            if user[1] >= min_videos:
                log.info( json.dumps( { 'message' : 'Adding user_id %s with %s videos to build user list.' % ( user[0], user[1] ) } ) )
                build_users.append( user[0] )
    else:
        # Get only eligible users who do not already have this content.
        all_users = []
        already_have = []
        
        if user_uuid is None:
            all_users = orm.query( MediaAssetFeatures.user_id, func.count( distinct( MediaAssetFeatures.media_id ) ) ).filter( MediaAssetFeatures.feature_type == 'face' ).group_by( MediaAssetFeatures.user_id )
            already_have = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.content_type == 'Smiling Faces' ) )
        else:
            all_users = orm.query( MediaAssetFeatures.user_id, func.count( distinct( MediaAssetFeatures.media_id ) ) ).filter( and_( MediaAssetFeatures.user_id == user.id, MediaAssetFeatures.feature_type == 'face' ) ).group_by( MediaAssetFeatures.user_id )

            already_have = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.content_type == 'Smiling Faces', ViblioAddedContent.user_id == user.id ) )
                
        already_have_dict = {}
        for content in already_have:
            user_id = content.user_id
            status = content.status
            attempts = content.attempts
            if status == 'scheduled' and attempts < max_retries:
                log.info( json.dumps( { 'message' : 'Adding previously scheduled user_id %s who is on attempt %s to build user list.' % ( user_id, attempts ) } ) )
            else:
                already_have_dict[user_id] = True

        for user in all_users:
            if user[1] >= min_videos and user[0] not in already_have_dict:
                log.info( json.dumps( { 'message' : 'Adding user_id %s with %s videos to build user list.' % ( user[0], user[1] ) } ) )
                build_users.append( user[0] )
        
    log.info( json.dumps( { 'message' : 'Adding smiling faces task for users: %s' % ( build_users ) } ) )
    
    queue = None
    if len( build_users ):
        queue = boto.sqs.connect_to_region( config.sqs_region, 
                                            aws_access_key_id = config.awsAccess, 
                                            aws_secret_access_key = config.awsSecret ).get_queue( config.smile_creation_queue )

    for user_id in build_users:
        user = orm.query( Users ).filter( Users.id == user_id ).one()
        
        smiling_faces = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.user_id == user_id, ViblioAddedContent.content_type == 'Smiling Faces' ) )[:]

        smiling_face = None

        if len( smiling_faces ) > 1:
            log.error( json.dumps( { 'message' : 'Error, more than 1 smiling face row for user %s found.' % ( user_id ) } ) )
        elif len( smiling_faces ) == 1:
            smiling_face = smiling_faces[0]
            smiling_face.status = 'scheduled'
            smiling_face.attempts += 1
        else:
            smiling_face = ViblioAddedContent( 
                content_type = 'Smiling Faces',
                status = 'scheduled',
                attempts = 1
                )
            user.viblio_added_content.append( smiling_face )

        orm.commit()

        if smiling_face is not None:
            log.info( json.dumps( { 'message' : 'Starting job for user_uuid: %s, viblio_added_content_id: %s, attempts: %s' % ( user.uuid, smiling_face.id, smiling_face.attempts ) } ) )
            message = Message()
            message.set_body( json.dumps( {
                        'user_uuid' : user.uuid,
                        'viblio_added_content_id' : smiling_face.id } ) )

            status = queue.write( message )
            log.info( json.dumps( { 'message' : 'Message status was: %s' % ( status ) } ) )
            
if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-v 5] [-u user-uuid] [-r 4] [-f]"

    parser = OptionParser( usage = usage )
    parser.add_option("-v", "--videos",
                      dest="videos",
                      help="Optional, defaults to 5. The minimum number of videos with faces a user must have before we build their smiling faces summary." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="Optional, defaults to all users who meet the -v criteria.  The user uuid of the user to build the summary for." )
    parser.add_option("-r", "--retries",
                      dest="retries",
                      help="Optional, defaults to 4.  The maximum number of retries that will be attempted if this content has been generated in the past and is not yet completed." )
    parser.add_option("-f", "--force",
                      action='store_true',
                      dest="force",
                      help="Generate the summary even if the summary has previously been generated for this user." )

    (options, args) = parser.parse_args()

    min_videos = 5
    if options.videos:
        min_videos = int( options.videos )

    user_uuid = None
    if options.user_uuid:
        user_uuid = options.user_uuid

    max_retries = 4
    if options.retries:
        max_retries = int( options.retries )

    force = False
    if options.force:
        force = True

    call_build_smiling_faces( min_videos, user_uuid, max_retries, force )

