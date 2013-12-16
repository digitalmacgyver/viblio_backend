#!/usr/bin/env python

import logging

from sqlalchemy import and_, not_, or_

import vib.cv.FaceRecognition as rec

import vib.db.orm
from vib.db.models import *

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

orm = vib.db.orm.get_session()

faces = orm.query( MediaAssetFeatures.id,
                   MediaAssetFeatures.user_id,
                   MediaAssetFeatures.contact_id,
                   MediaAssetFeatures.media_asset_id,
                   MediaAssetFeatures.detection_confidence,
                   MediaAssets.uri
                   ).filter( and_(
        MediaAssets.id == MediaAssetFeatures.media_asset_id,
        MediaAssetFeatures.contact_id != None,
        MediaAssetFeatures.feature_type == 'face',
        or_( MediaAssetFeatures.recognition_result == None, not_( MediaAssetFeatures.recognition_result.in_( [ 'bad_track', 'bad_face', 'two_face', 'not_face' ] ) ) ) ) )
                             #MediaAssetFeatures.id > 4601


faces_by_user = {}

for face in faces:
    score = 0
    #if face.detection_confidence is not None:
    #    score = face.detection_confidence
    print "Working on %s, %s, %s, %s, %s" % ( face.user_id, face.contact_id, face.id, face.uri, score )
    
    face_input = {
        'user_id'     : face.user_id,
        'contact_id'  : face.contact_id,
        'face_id'     : face.id,
        'face_url'    : config.ImageServer + face.uri,
        'external_id' : face.media_asset_id,
        'score'       : score
        }

    if face.user_id not in faces_by_user:
        faces_by_user[face.user_id] = { face.contact_id : [ face_input ] }
    elif face.contact_id not in faces_by_user[face.user_id]:
        faces_by_user[face.user_id][face.contact_id] = [ face_input ]
    else:
        faces_by_user[face.user_id][face.contact_id].append( face_input )

for user in faces_by_user:
    for contact in faces_by_user[user]:
        faces = faces_by_user[user][contact]
        print "\n\nWORKING ON USER %s, CONTACT %s ADDING %s FACES\n\n" % ( user, contact, len( faces ) )
        rec.add_faces( user, contact, faces )
