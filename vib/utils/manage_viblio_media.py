#!/usr/bin/env python

import logging
from optparse import OptionParser
import os
import sys
import sqlalchemy
from sqlalchemy import and_
import uuid

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.clone_user' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'manage_viblio_media: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def manage_media( action, title, media_type, desc, album_title, filename ):
    # Check if this thing exists.
    orm = vib.db.orm.get_session()
    
    user = orm.query( Users ).filter( Users.id == config.viblio_media_user_id ).one()
    
    media = orm.query( Media ).filter( and_( Media.user_id == config.viblio_media_user_id,
                                             Media.title == title,
                                             Media.media_type == media_type ) )[:]
    
    if len( media ) > 1:
        raise Exception( "%d media items of type, title: %s, %s found for for viblio_media_user_id: %d, expected 0 or 1, quiting." % ( len( media ), media_type, title, config.viblio_media_user_id ) )
    elif action == 'add' and len( media ):
        raise Exception( "There is already a media of type, title: %s, %s for viblio_media_user_id: %d" % ( media_type, title, config.viblio_media_user_id ) )
    elif action == 'delete' and not len( media ):
        raise Exception( "No media of type, title: %s, %s found to delete for viblio_media_user_id: %d" % ( media_type, title, config.viblio_media_user_id ) )
    
    if action == 'add':
        media_uuid = str( uuid.uuid4() )
        asset_uuid = str( uuid.uuid4() )
        
        print "Adding %s with media_uuid: %s and asset_uuid: %s" % ( filename, media_uuid, asset_uuid )
        
        s3.upload_file( filename, config.bucket_name, "%s/%s" % ( media_uuid, media_uuid ) )
        
        media = Media( user_id = user.id,
                       uuid = media_uuid,
                       media_type = media_type,
                       title = title,
                       filename = filename,
                       description = desc,
                       is_viblio_created = 1 )
        
        user.media.append( media )
        
        mime = magic.Magic( mime=True )
        
        asset = MediaAssets( uuid = asset_uuid,
                             asset_type = 'original',
                             mimetype = mime.from_file( filename ),
                             uri = "%s/%s" % ( media_uuid, media_uuid ),
                             location = 'us',
                             bytes = os.path.getsize( filename ) )
        
        media.media_assets.append( asset )
        
        if album_title is not None:
            album = orm.query( Media ).filter( and_( Media.user_id == user.id,
                                                     Media.title == album_title,
                                                     Media.is_album == 1 ) )[:]
            
            print "Adding to album: %s, %s" % ( album.title, album.id )
            
            if len( album ) != 1:
                print "Warning - less or more than 1 albums named %s found for viblio media user, no album association made." % ( album )
            else:
                album.media_albums.append( media )
                
        orm.commit()
    elif action == 'add_album':      
        print "Creating %s album %s" % ( media_type, title )
        media_uuid = str( uuid.uuid4() )
        
        media = Media( user_id = user.id,
                       uuid = media_uuid,
                       media_type = media_type,
                       title = album_title,
                       is_album = 1,
                       description = description,
                       is_viblio_created = 1 )

        user.media.append( media )

        orm.commit()
    if action == 'delete':
        print "Deleting %s, %s" % ( media_type, title )
        orm.query( Media ).filter( and_( Media.user_id == user.id,
                                         Media.is_viblio_created == 1,
                                         Media.media_type == media_type,
                                         Media.title == title ) )
        orm.commit()
        s3.delete_s3_file( config.bucket_name, "%s/%s" % ( media.uuid, media.uuid ) )
        

if __name__ == '__main__':
    usage = "Managed Viblio owned media for the admin@viblio.com account usage:\nDEPLOYMENT=[staging|prod] %prog --add|--add-album|--delete --title=T --type=[music] [--desc=D] [--album=Aname] [--filename=F]" 

    parser = OptionParser( usage = usage )
    parser.add_option( "-a", "--add",
                       dest="add",
                       help="Add the media argument to --filename (mutually exclusive with --add-album and --delete)" )
    parser.add_option( "-A", "--add-album",
                       dest="add_album",
                       help="Create an album with --title (mutually exclusive with --add and --delete)" )
    parser.add_option( "-d", "--delete",
                       dest="delete",
                       help="Remove the media specified by title/type (mutually exclusive with --add and --add-album)" )
    parser.add_option( "-t", "--title",
                       dest="title",
                       help="Specify the title of the media being added/deleted." )
    parser.add_option( "-e", "--desc",
                       dest="desc",
                       help="Specify the description of the media being added/deleted." )
    parser.add_option( "-y", "--type",
                       dest="type",
                       help="Specify the description of the media being added/deleted." )
    parser.add_option( "-l", "--album",
                       dest="album",
                       help="The name of the album created with --add-album or added to with --add." )
    parser.add_option( "-f", "--filename",
                       dest="filename",
                       help="Specify the media file to be added." )

    (options, args) = parser.parse_args()

    action = None
    filename = None
    title = None
    media_type = None
    desc = ""
    album_title = None

    media_types = [ 'music' ]

    if not ( options.add or options.delete or options.add_album ):
        parser.print_help()
        print "\n\nMust provide either --add, -add-album, or --delete arguments."
        sys.exit(0)
    elif ( options.add and options.add_album ) or ( options.add and options.delete ) or ( options.add_album and options.delete ):
        parser.print_help()
        print "\n\nMust provide only one of --add, --add-album, or --delete arguments."
        sys.exit(0)
    elif options.delete:
        action = 'delete'
    elif options.add_album:
        action = 'add_album'
    else:
        action = 'add'
        
        if not options.filename:
            print "\n\nMust provide --filename argument for --add."
            parser.print_help()
            sys.exit(0)
        else:
            if os.path.exists( options.filename ):
                filename = options.filename
            else:
                raise Exception( "Error - could not locate input file at: %s" % ( options.filename ) )

    if action != 'add_album' and ( not options.title or not options.type ):
        parser.print_help()
        print "\n\nMust provide both --title and --type."
        sys.exit(0)
    elif action == 'add_album' and not options.type:
        parser.print_help()
        print "\n\nMust provide --type."
        sys.exit(0)
    else:
        title = options.title
        if media_type in media_types:
            media_type = options.type
        else:
            parser.print_help()
            print "\n\n--type must be one of: %s" % ( media_types )
            sys.exit(0)

    if options.desc:
        desc = options.desc
        
    if options.album:
        album_title = options.album
            
    manage_media( action, title, media_type, desc, album_title, filename )
        
