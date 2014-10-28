#!/usr/bin/env python

import logging
from optparse import OptionParser
import re
from sqlalchemy import and_, not_
import sys
import uuid

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *


log = logging.getLogger( 'vib.utils.create-email-alias' )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'create-email-alias: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

def get_uuid_for_email( email ):
    orm = vib.db.orm.get_session()

    uuids = []

    for user in orm.query( Users ).filter( Users.email == email ):
        uuids.append( user.uuid )

    return uuids


def populate_contacts( alias_file, user_uuid, group_name ):
    contacts = {}

    with open( alias_file, 'r' ) as afile:
        for oline in afile:
            try:
                # Skip blank lines.
                if re.match( r'^\s*$', oline ):
                    continue

                line = oline.rstrip()
                email, fname, lname = line.split( '\t' )

                # DEBUG - for testing.
                print "Email before: %s" % ( email )
                email = email.split( '@' )[0]
                email = "mjhayward+%s@gmail.com" % ( email )

                print "Email: '%s', First: '%s', Last: '%s'" % ( email, fname, lname )
                if email in contacts:
                    raise Exception( "Duplicate email found: '%s': %s" % ( email, contacts[email] ) )
                else:
                    contacts[email] = { 'fname' : fname,
                                        'lname' : lname }
            except Exception as e:
                print "ERROR: Failed to process line '%s', error was: %s" % ( oline, e )

    orm = vib.db.orm.get_session()

    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

    # Get the desired contact group.
    contact_groups = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.is_group == True, Contacts.contact_name == group_name ) ).all()
    contact_group = None
    if len( contact_groups ) > 1:
        print "WARNING: Multiple existing contact groups for user: %d with name: %s, using this one: %d" % ( user.id, group_name, contact_groups[0].id )        
        contact_group = contact_groups[0]
    elif len( contact_groups ) == 1:
        contact_group = contact_groups[0]
        print "Found existing contact group: %d for %s" % ( contact_group.id, group_name )
    else:
        contact_group = Contacts( uuid = str( uuid.uuid4() ),
                                  is_group = True,
                                  contact_name = group_name )
        user.contacts.append( contact_group )
        orm.commit()
        print "Created new contact group: %d for %s" % ( contact_group.id, group_name )

    # Find / Create contacts as needed and add them to our group.
    for email, details in contacts.items():
        fname = contacts[email]['fname']
        lname = contacts[email]['lname']
        
        # Create the contact if it doesn't exist.
        existing_contact = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.contact_email == email, Contacts.is_group == False ) ).all()
        contact = None
        if len( existing_contact ) > 1:
            print "WARNING: Multiple existing contacts for user: %d with email: %s, using this one: %d" % ( user.id, email, existing_contact[0].id )
            contact = existing_contact[0]
        elif len( existing_contact ) == 1:
            contact = existing_contact[0]
            print "Found existing contact: %d for %s" % ( contact.id, email )
        else:
            # Check if there is a contact of this name without an email.
            name = "%s %s" % ( fname, lname )
            existing_contact = orm.query( Contacts ).filter( and_( Contacts.user_id == user.id, Contacts.contact_email is None, Contacts.contact_name == name, Contacts.is_group == False ) ).all()
            if len( existing_contact ) > 1:
                print "WARNING: Multiple existing contacts for user: %d with no email and name: %s, using this one: %d" % ( user.id, name, existing_contact[0].id )
                contact = existing_contact[0]
            elif len( existing_contact ) == 1:
                contact = existing_contact[0]
                print "Found existing contact: %d for %s" % ( contact.id, email )
            else:
                # Create a contact.
                contact = Contacts( uuid     = str( uuid.uuid4() ),
                                    is_group = False,
                                    contact_name = name,
                                    contact_email = email )
                user.contacts.append( contact )
                orm.commit()
                print "Created new contact: %d for %s" % ( contact.id, email )

        # Add the contact to the contact_group if necessary.
        in_group_already = orm.query( ContactGroups ).filter( and_( ContactGroups.group_id == contact_group.id, ContactGroups.contact_id == contact.id ) ).all()
        if len( in_group_already ) == 0:
            add_to_group = ContactGroups( group_id = contact_group.id,
                                          contact_id = contact.id )
            orm.add( add_to_group )
            orm.commit()
            print "Added contact %d for %s to group %d named %s." % ( contact.id, contact.contact_email, contact_group.id, contact_group.contact_name )
        else:
            print "Contact %d for %s already in group %d named %s." % ( contact.id, contact.contact_email, contact_group.id, contact_group.contact_name )

if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog -e user@email.com | -u user-uuid -f contact_file -g GroupName"

    parser = OptionParser( usage = usage )
    parser.add_option("-e", "--email",
                  dest="email",
                  help="Print the uuid(s) associated with the email and exit." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The user uuid of the user who will own the contact group." )
    parser.add_option("-f", "--file",
                      dest="alias_file",
                      help="The path to the tab seperated file that contains 'email fname lname'" )
    parser.add_option("-g", "--group-name",
                      dest="group_name",
                      help="The name of the contact group to add the users in -f to." )

    (options, args) = parser.parse_args()

    if not ( options.email or options.user_uuid ):
        parser.print_help()
        sys.exit(0)
    elif options.email:
        email = options.email

        found = False

        for uuid in get_uuid_for_email( email ):
            print "Found uuid:", uuid, "for email:", email
            found = True

        if not found:
            print "No user found for email:", email

    elif options.user_uuid and options.alias_file and options.group_name:
        user_uuid = options.user_uuid
        alias_file = options.alias_file
        group_name = options.group_name

        # For testing.
        alias_file = '/wintmp/alias/2015.txt'
        # mjhayward+groupstest in staging.
        user_uuid = 'A614BCB0-5E16-11E4-83EF-D0E2CA5D5AE2'
        group_name = 'TestGroup'

        populate_contacts( alias_file, user_uuid, group_name )
    else:
        print "Must provide either -e or all of -u, -f, and -g arguments."





