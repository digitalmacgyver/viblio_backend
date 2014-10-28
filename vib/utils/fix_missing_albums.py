#!/usr/bin/env python

from sqlalchemy import and_, not_
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3

from vib.db.models import *
import vib.db.orm

orm = vib.db.orm.get_session()

no_poster_albums = orm.query( Media ).filter( and_( Media.media_type == 'original', 
                                                    Media.is_album == True,
                                                    ~Media.assets.any( MediaAssets.asset_type == 'poster' ) ) )
# DEBUG
#Media.user_id == 604
#) )

poster_uris = {
    'Birthdays' : { 'size' : 19460, 'uri' : 'media/default-images/BIRTHDAY-poster.jpg' },
    'Family'    : { 'size' : 17479, 'uri' : 'media/default-images/FAMILY-poster.jpg' },
    'Friends'   : { 'size' : 15943, 'uri' : 'media/default-images/FRIENDS-poster.jpg' },
    'Holidays'  : { 'size' : 17789, 'uri' : 'media/default-images/HOLIDAY-poster.jpg' },
    'Vacations' : { 'size' : 17518, 'uri' : 'media/default-images/VACATION-poster.jpg' }
}

for album in no_poster_albums:
    try:
        poster_uri = 'media/default-images/DEFAULT-poster.png'
        poster_mimetype = 'image/png';
        poster_size = 7087
        poster_width = 288
        poster_height = 216
        if album.title in poster_uris:
            poster_uri = poster_uris[album.title]['uri']
            poster_size = poster_uris[album.title]['size']
            poster_mimetype = 'image/jpeg'
        
        poster_uuid = str( uuid.uuid4() )

        poster_dest_uri = "%s/%s_poster.png" % ( album.uuid, album.uuid )
    
        s3.copy_s3_file( 'viblio-external', poster_uri, config.bucket_name, poster_dest_uri )

        poster_asset = MediaAssets( uuid = poster_uuid,
                                    asset_type = 'poster',
                                    mimetype = poster_mimetype,
                                    uri = poster_dest_uri,
                                    bytes = poster_size,
                                    width = poster_width,
                                    height = poster_height )

        album.assets.append( poster_asset )
        orm.commit()
    except Exception as e:
        print "ERROR: Failed to add poster for album id: %d, error was: %s" % ( album.id, e )


