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

format_string = 'call_build_album_summaries: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def call_build_album_summaries( min_videos = 5, album_uuid = None, max_retries = 4, force = False ):
    log.info( json.dumps( { 'message' : 'Processing with min_videos: %s, album_uuid: %s, max_retries: %s force: %s' % ( min_videos, album_uuid, max_retries, force ) } ) )
    
    orm = vib.db.orm.get_session()
    orm.commit()

    album_id = None
    if album_uuid is not None:
        album = orm.query( Media ).filter( and_( Media.uuid == album_uuid, Media.is_album == True ) ).one()
        album_id = album.id
        
    build_albums = [];

    if force:
        # Get all eligible albums regardless of status in viblio_added_content
        all_albums = None
        if album_uuid is None:
            # Find any album with at least min_videos
            all_albums = orm.query( MediaAlbums.album_id, func.count( distinct( MediaAlbums.media_id ) ) ).group_by( MediaAlbums.album_id )
        else:
            all_albums = orm.query( MediaAlbums.album_id, func.count( distinct( MediaAlbums.media_id ) ) ).filter( MediaAlbums.album_id == album_id ).group_by( MediaAlbums.album_id )

        for album in all_albums:
            if album[1] >= min_videos:
                log.info( json.dumps( { 'message' : 'Adding album_id %s with %s videos to build user list.' % ( album[0], album[1] ) } ) )
                build_albums.append( album[0] )
    else:
        # Get only eligible albums who do not already have this content.
        all_albums = []
        already_have = []
        
        if album_uuid is None:
            all_albums = orm.query( MediaAlbums.album_id, func.count( distinct( MediaAlbums.media_id ) ) ).group_by( MediaAlbums.album_id )
            already_have = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.content_type == 'Album Summary' ) )
        else:
           all_albums = orm.query( MediaAlbums.album_id, func.count( distinct( MediaAlbums.media_id ) ) ).filter( MediaAlbums.album_id == album_id ).group_by( MediaAlbums.album_id )
           already_have = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.content_type == 'Album Summary', ViblioAddedContent.album_id == album_id ) )
                
        already_have_dict = {}
        for content in already_have:
            user_id = content.user_id
            status = content.status
            content_album_id = content.album_id
            attempts = content.attempts
            if status == 'scheduled' and attempts < max_retries:
                log.info( json.dumps( { 'message' : 'Adding previously scheduled album_id %s who is on attempt %s to build summary.' % ( content_album_id, attempts ) } ) )
            else:
                already_have_dict[content_album_id] = True

        for album in all_albums:
            if album[1] >= min_videos and album[0] not in already_have_dict:
                log.info( json.dumps( { 'message' : 'Adding album_id %s with %s videos to build list.' % ( album[0], album[1] ) } ) )
                build_albums.append( album[0] )
        
    log.info( json.dumps( { 'message' : 'Adding summary task for albums: %s' % ( build_albums ) } ) )
    
    queue = None
    if len( build_albums ):
        queue = boto.sqs.connect_to_region( config.sqs_region, 
                                            aws_access_key_id = config.awsAccess, 
                                            aws_secret_access_key = config.awsSecret ).get_queue( config.album_summary_creation_queue )

    for album_id in build_albums:
        album = orm.query( Media ).filter( Media.id == album_id ).one()
        
        album_summaries = orm.query( ViblioAddedContent ).filter( and_( ViblioAddedContent.album_id == album_id, ViblioAddedContent.content_type == 'Album Summary' ) )[:]

        if len( album_summaries ) > 1:
            log.error( json.dumps( { 'message' : 'Error, more than 1 album summary row for album %s found.' % ( album_id ) } ) )
            continue

        # Find out what sort of album summary we'd like to make.
        # 
        # If this is a person album, make a person summary. 
        # 
        # Other album types not yet implemented.
        contacts = orm.query( Contacts ).filter( Contacts.user_id == album.user_id )
        contact_id = None
        for contact in contacts:
            if album.title == contact.contact_name:
                contact_id = contact.id
                break
                
        if contact_id is not None:
            if len( album_summaries ) == 1:
                album_summary = album_summaries[0]
                album_summary.status = 'scheduled'
                album_summary.attempts += 1
            else:
                album_summary = ViblioAddedContent( 
                    content_type = 'Album Summary',
                    status = 'scheduled',
                    attempts = 1,
                    user_id = album.user_id,
                    album_id = album.id,
                    album_user_id = album.user_id,
                    )
                orm.add( album_summary )
            orm.commit()
            log.info( json.dumps( { 'message' : 'Starting job for person album_uuid: %s, viblio_added_content_id: %s, attempts: %s' % ( album.uuid, album_summary.id, album_summary.attempts ) } ) )
            message = Message()
            message.set_body( json.dumps( {
                        'album_uuid' : album.uuid,
                        'viblio_added_content_id' : album_summary.id,
                        'summary_type' : 'person',
                        'contact_id' : contact_id } ) )
                
            status = queue.write( message )
            log.info( json.dumps( { 'message' : 'Message status was: %s' % ( status ) } ) )
        else:
            log.info( json.dumps( { 'message' : 'Skipping job for non-person album_uuid: %s' % ( album.uuid ) } ) )
            
if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-v 5] [-a album-uuid] [-r 4] [-f]"

    parser = OptionParser( usage = usage )
    parser.add_option("-v", "--videos",
                      dest="videos",
                      help="Optional, defaults to 5. The minimum number of videos with faces an album must have before we build their summary." )
    parser.add_option("-a", "--album",
                      dest="album_uuid",
                      help="Optional, defaults to all albums who meet the -v criteria.  The album uuid of the album to build the summary for." )
    parser.add_option("-r", "--retries",
                      dest="retries",
                      help="Optional, defaults to 4.  The maximum number of retries that will be attempted if this content has been generated in the past and is not yet completed." )
    parser.add_option("-f", "--force",
                      action='store_true',
                      dest="force",
                      help="Generate the summary even if the summary has previously been generated for this album." )

    (options, args) = parser.parse_args()

    min_videos = 5
    if options.videos:
        min_videos = int( options.videos )

    album_uuid = None
    if options.album_uuid:
        album_uuid = options.album_uuid

    max_retries = 4
    if options.retries:
        max_retries = int( options.retries )

    force = False
    if options.force:
        force = True

    call_build_album_summaries( min_videos, album_uuid, max_retries, force )

