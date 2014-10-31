#!/usr/bin/env python

import logging
from optparse import OptionParser
import re
from sqlalchemy import and_, exists
import sys

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *
import vib.cv.FaceRecognition.api as rec

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( 'vib.utils.face_fixer' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'face_fixer: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def fix_faces( report = True ):
    '''If report is true just print out what would happen, but don't
       change anything.  If report is false actually do the
       changes.
    '''

    orm = vib.db.orm.get_session()
    
    uris = {}
    db_uris = orm.query( MediaAssets.uri ).filter( and_( MediaAssets.uri is not None, MediaAssets.asset_type.in_( [ 'face', 'fb_face' ] ) ) )
    for uri in db_uris:
        uris[uri[0]] = True

    # Get a list of contacts whose picture URI is not in the database.
    bad_contacts = []
    for contact in orm.query( Contacts ).filter( Contacts.picture_uri is not None ):
        if contact.picture_uri not in uris:
            bad_contacts.append( contact )

    for bc in bad_contacts:
        print "Bad contact: %s" % ( bc.id ),

        if re.search( r'_fb_face', bc.uri ):
            # This is a Facebook URI
            if s3.check_exists( config.bucket_name, bc.uri ):
                print "Valid FB URI, ignoring."
                continue

        # If there is another media_asset_feature for that contact,
        # set the picture URI to that.
        # First see if we have one from videos:
        features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.contact_id == bc.id, MediaAssetFeatures.user_id == bc.user_id, MediaAssetFeatures.feature_type == 'face' ) )[:]
        
        if len( features ) > 0:
            uri = features[0].media_assets.uri
            print "Setting picture URI to video face: %s" % ( uri )
            bc.picture_uri = uri
            if not report:
                orm.commit()
        else:
            fb_features = orm.query( MediaAssetFeatures ).filter( and_( MediaAssetFeatures.contact_id == bc.id, MediaAssetFeatures.user_id == bc.user_id, MediaAssetFeatures.feature_type == 'fb_face' ) )[:]

            if len( fb_features ) > 0:
                uri = fb_features[0].media_assets.uri
                print "Setting picture URI to FB face: %s" % ( uri )
                bc.picture_uri = uri                
                if not report:
                    orm.commit()
            elif bc.contact_name is not None:
                print "Removing picture URI for %s who has no images" % ( bc.contact_name )
                bc.picture_uri = None
                if not report:
                    orm.commit()
            else:
                print "Deleting unidentified contact id: %s" % ( bc.id )
                orm.delete( bc )
                if not report:
                    orm.commit()

report = True

fix_faces( report )
