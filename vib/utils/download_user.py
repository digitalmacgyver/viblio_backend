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

format_string = 'clone_user: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

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

def download_user( user_uuid, outdir='/wintmp/vibout/test/', verbose=False ):
    orm = None

    try:
        #import pdb
        #pdb.set_trace()

        orm = vib.db.orm.get_session()
    
        users = orm.query( Users ).filter( Users.uuid == user_uuid )

        if users.count() != 1:
            print "Found %s users with uuid %s, can't clone, returning." % ( users.count(), user_uuid )
            return 0

        user = users[0]
        old_user_id = user.id

        picture_uris = {}
        contact_ids = {}

        media_files = orm.query( Media ).filter( and_( Media.user_id == old_user_id, Media.media_type == 'original', Media.is_album == False ) )[:]

        seen_outnames = {}

        # Download Media
        for m in media_files:
            try:
                if not m.is_album:
                    if verbose:
                        print "Working on media_file:", m.id, m.filename, m.created_date
                
                    original_filename = m.filename

                    if m.is_viblio_created:
                        original_filename = m.title

                    created_date = m.created_date

                    outname = ""
                    outext = ".mp4"
                    
                    use_created_date = False

                    if len( original_filename ) == 0:
                        # Set filename based on created_date
                        use_created_date = True
                    else:
                        filename_full = os.path.split( original_filename )[-1]
                        ( filename, ext ) = os.path.splitext( filename_full )
                        if len( filename ):
                            outname = filename
                            if len( ext ) != 0:
                                outext = ext
                        else:
                            # set filename based on created date
                            use_created_date = True
                    
                    if use_created_date:
                        outname = created_date.strftime( "%Y-%m-%d_%H-%M-%S" )

                    tmp_outname = ''
                    for ch in outname:
                        if ch in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ':
                            tmp_outname += ch
                        else:
                            tmp_outname += '_'

                    outname = tmp_outname
                    outname = outname.strip()
                    outext = outext.strip()

                    if outname in seen_outnames:
                        seen_outnames[outname] += 1
                        outname += "_%d" % ( seen_outnames[outname] )
                    else:
                        seen_outnames[outname] = 1

                    # Work on assets.
                    assets = orm.query( MediaAssets ).filter( MediaAssets.media_id == m.id )[:]

                    seen_imagenames = {}

                    for asset in assets:
                        try:
                            if asset.asset_type not in [ 'image', 'main', 'original', 'poster', 'poster_animated', 'poster_original', 'thumbnail', 'thumbnail_animated' ]:
                                continue

                            if asset.uri is None:
                                print "Warning, null old_uri for asset: %s" % ( asset.uuid )
                                continue
                                
                            if verbose:
                                print "\tWorking on asset:", asset.asset_type, asset.id

                            base_dir = outdir + "/" + outname + "/"
                            image_dir = outdir + "/" + outname + "/photos/"

                            if not os.path.exists( base_dir ):
                                os.makedirs( base_dir )
                            if not os.path.exists( image_dir ):
                                os.makedirs( image_dir )
                                
                            download_name = None

                            if asset.asset_type == 'main':
                                download_name = base_dir + outname + "_Viblio.mp4"
                            elif asset.asset_type == 'original':
                                download_name = base_dir + outname + outext
                            elif asset.asset_type == 'image':
                                download_name = str( int( asset.timecode ) )
                                if download_name in seen_imagenames:
                                    seen_imagenames[download_name] += 1
                                    download_name += "_%d" % ( seen_imagenames[download_name] )
                                else:
                                    seen_imagenames[download_name] = 1
                                download_name += os.path.splitext( asset.uri )[-1]
                                download_name = image_dir + download_name
                            else:
                                download_name = image_dir + asset.asset_type + os.path.splitext( asset.uri )[-1]

                            if not os.path.exists( download_name ):
                                s3.download_file( download_name, config.bucket_name, asset.uri )
                                #print "DOWNLOAD", download_name
                            else:
                                print "Skpping download of duplicate file:", download_name
                                # DEBUG
                                #addaprint "DOWNLOAD", download_name

                        except Exception as e:
                            print "Error with asset:", e
            except Exception as e:
                print "Error with media file", e

        if verbose:
            print "Done"

    except Exception as e:
        print "Error: %s, rolling back (note: s3 operations can not be rolled back)" % ( e )

        if orm:
            orm.rollback()

if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-e user@email.com][-u user-uuid][-d outputdir]"
    parser = OptionParser( usage = usage )
    parser.add_option("-e", "--email",
                  dest="email",
                  help="Download files for the email, or if more than one uuid is present for that email print them." )
    parser.add_option("-d", "--outdir",
                      dest="output_dir",
                      help="The directory where output is stored, defaults to ./email with @ removed." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The user uuid of the user to download." )

    (options, args) = parser.parse_args()

    if not ( options.email ):
        parser.print_help()
        sys.exit(0)
    
    email = options.email

    uuids = get_uuid_for_email( email )

    if len( uuids ) == 0:
        print "No user found for email:", email
        sys.exit( 0 )
    elif len( uuids ) > 1:
        if options.user_uuid:
            user_uuid = options.user_uuid
        else:
            print "Found multiple uuids for that email, please disambiguate by specifying one uuid with -u."
            for uuid in uuids:
                print "Found uuid:", uuid, "for email:", email
            sys.exit( 0 )
    else:
        user_uuid = uuids[0]

    outdir = email.replace( '@', '_' )

    if options.output_dir:
        outdir = options.output_dir

    download_user( user_uuid, outdir, verbose=True )

