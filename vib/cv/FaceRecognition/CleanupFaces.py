import json
import logging
from logging import handlers
from sqlalchemy import not_
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.db.orm
from vib.db.models import *

import vib.cv.FaceRecognition.api as rec

log = logging.getLogger( 'vib.cv.CleanupFaces' )
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
                                 'message' : "Failed to delete contact: %s" % ( e ) } ) )
        raise

def run():
    try:
        orm = vib.db.orm.get_session()

        missing_contacts = orm.query( Faces2 ).filter( not_( Faces2.contact_id.in_( orm.query( Contacts.id ) ) ) )

        deleted_contacts = {}

        for contact in missing_contacts:
            user_id = contact.user_id
            contact_id = contact.contact_id
            if user_id not in deleted_contacts:
                deleted_contacts[user_id] = { contact_id : True }
                delete_contact( contact.user_id, contact.contact_id )
            elif contact_id not in deleted_contacts[user_id]:
                deleted_contacts[user_id][contact_id] = True
                delete_contact( contact.user_id, contact.contact_id )
            else:
                log.debug( json.dumps( { 'user_id' : user_id,
                                         'contact_id' : contact_id,
                                         'message' : 'Already deleted user, contact: %s, %s' % ( user_id, contact_id ) } ) )

    except Exception as e:
        log.error( json.dumps( { 'message' : 'Exception was %s' % ( e ) } ) )
        raise
