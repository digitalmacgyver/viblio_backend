#!/usr/bin/env python

import boto.sqs
import boto.sqs.connection
from boto.sqs.message import RawMessage
import datetime
import json
import logging
from optparse import OptionParser
import random
import sys
import sqlalchemy
from sqlalchemy import and_, distinct, func
import time
import uuid

import vib.db.orm
from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
log.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'year_in_review_summary: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

log.addHandler( syslog )
log.addHandler( consolelog )

total_duration = 120
clip_duration = 4.0
#clip_count = total_duration / clip_duration
clip_count = 48

def call_build_video_summary( user_uuid, year ): 
    orm = vib.db.orm.get_session()
    orm.commit()
    
    #import pdb
    #pdb.set_trace()

    user = orm.query( Users ).filter( Users.uuid == user_uuid ).one()

    # Get a list of the movies from this user from this year.
    from_when = datetime.date( year-1, 12, 31)
    to_when = datetime.date( year+1, 1, 1)
    
    movies = orm.query( Media, MediaAssets ).filter( and_(
        Media.id == MediaAssets.media_id,
        Media.user_id == user.id,
        #MediaAlbums.album_id == album_id,
        #MediaAlbums.media_id == Media.id,
        Media.recording_date > from_when,
        Media.recording_date < to_when,
        Media.is_album == False,
        Media.media_type == 'original',
        MediaAssets.asset_type == 'main',
        Media.status.in_( [ 'visible', 'complete' ] ),
        Media.is_viblio_created == False
        ) ).order_by( Media.recording_date ).all()

    #album = orm.query( Media ).filter( Media.id == album_id ).one()

    print "There are initially: %d movies." % ( len( movies ) )

    if len( movies ) > clip_count:
        movies = movies[0::( 1 + len( movies ) / clip_count )]

    print "Now there are: %d movies." % ( len( movies ) )

    movie_count = len( movies )

    clips_per_movie = int( max( 1 + clip_count / movie_count, 2 ) )

    print "We want: %d clips per movie." % ( clips_per_movie )

    selected_images = []

    simple = False

    for movie in movies:
        images = orm.query( MediaAssets ).filter( and_( 
            MediaAssets.media_id == movie.Media.id,
            MediaAssets.asset_type == 'image' ) ).order_by( MediaAssets.timecode )

        if simple:
            selected_images += [ x.uuid for x in images ]
        else:
            print "Working on %s" % ( movie.Media.title )
            
            duration = movie.MediaAssets.duration
            if duration is None:
                duration = images[-1].timecode + 1
            if duration is None:
                continue

            print "Of duration: %f" % ( duration )

            ideal_offsets = [ float( duration * ( x + 1 ) ) / ( clips_per_movie+1 ) for x in range( clips_per_movie ) ]

            print "Ideally we'll take %d clips from this movie." % ( len( ideal_offsets ) )

            current_offset = None
            used_images = {}

            for offset in ideal_offsets:
                for image in images:
                    if image.timecode >= offset:
                        if image.uuid in used_images:
                            continue
                        else:
                            selected_images.append( image.uuid )
                            used_images[ image.uuid ] = True
                            print "CLIP SELECTED"
                            break
            
    if simple:
        selected_images = selected_images[0::( 1 + len( selected_images ) / clip_count )]

    video_summary = {
        'action' : 'create_video_summary',
        'user_uuid' : user_uuid,
        'images[]' : selected_images,
        'summary_type' : 'moments',
        'audio_track' : 'f4a6501d-7f85-4040-92b5-e97d5a568c27',
        'summary_style' : 'template-2',
        'order' : 'oldest',
        'target_duration' : total_duration,
        'title' : 'VIBLIO: Year in Review',
    }

    songs = [
        #'c637ac8a-3b3f-4030-82a0-af423a227457',
        '2cecfbf0-66de-4947-a168-590ddc1f200f',
        'd105304f-6fae-4fab-8fc1-bfe1352100d3',
        'a75cd2de-0c62-4cb3-bc9c-245ecfda0da7',
        '5406e7f6-ea76-4f60-98d6-092df9a0b637',
        '1b324c07-945d-434f-926d-cc5095dabcc8',
        'f4a6501d-7f85-4040-92b5-e97d5a568c27',
        '11e033aa-464d-48af-979f-d30a359d1ff8',
        '9ad4e4ff-69a6-448d-ac44-b86cdbfa8d60',
        '0db07b3c-2cd2-4624-bd6a-43840ded3f4b',
        '756c6329-662e-46d4-9ea9-1223585c2487',
        'c6bfc438-fd26-4742-9b89-576132d86c61',
        'ff48a1f5-59ae-4c1a-be68-d842dc1a884f',
        #'9664ab37-68c8-4e8a-890a-327ec7ec7c5e',
        '82c7b7f7-272e-48ef-a989-942872b38456',
        '1d04fc52-93da-4182-8cff-428b27c49f09'
    ]

    songs = [
        #'1827e8a3-148f-4a50-a518-c96e5cfe2046', # staging - good riddance
        #'9ad4e4ff-69a6-448d-ac44-b86cdbfa8d60', # Staging - clocks in chicago
        #'6578e271-813b-4c1f-82cf-2cca0364550a', # prod - clocks in chicago
        '9a2fc139-3acb-48be-a334-bb02bda15ba5' #prod - good riddance
    ]
    
    use_sqs = True

    if use_sqs:
        summary_uuid = str( uuid.uuid4() )
        
        title = 'A Holiday Gift from VIBLIO'

        media = Media( uuid = summary_uuid,
                       status = 'pending',
                       media_type = 'original',
                       filename = '',
                       title = title,
                       description = '',
                       view_count = 0,
                       recording_date = datetime.datetime.now(),
                       is_viblio_created = 1,
                       user_id = user.id )

        orm.add( media )
        orm.commit()

        sqs = boto.sqs.connect_to_region( config.sqs_region, aws_access_key_id = config.awsAccess, aws_secret_access_key = config.awsSecret )

        q = sqs.get_queue( config.album_summary_creation_queue )
        m = RawMessage()
        
        m.set_body( json.dumps( {
            'audio_track' : random.choice( songs ),
            'summary_type' : 'moments',
            'summary_style' : 'template-2',
            'order' : 'oldest',
            'title' : title,
            'images[]' : video_summary['images[]'],
            'moment_offsets[]' : [ -clip_duration / 2.0, clip_duration / 2.0 ],
            'summary_options' : json.dumps( {
                'template' : 'email/27-yirSummary.tt',
                'subject' : title,
                'distribute_clips' : 'side_by_side',
                'holiday_card' : True,
                'duration_method' : 'shortest',
                'year_desc' : '2014'
            } ),
            'summary_uuid' : summary_uuid,
            'action' : 'create_video_summary',
            'user_uuid' : user.uuid,
        } ) )
        
        status = q.write( m )

        print "Status of write to SQS was: %s" % ( status )

def get_uuid_for_email( email ):
    orm = vib.db.orm.get_session()

    uuids = []

    for user in orm.query( Users ).filter( Users.email == email ):
        uuids.append( user.uuid )

    return uuids


if __name__ == '__main__':
    usage = "usage: DEPLOYMENT=[staging|prod] %prog [-e user@email.com]|[-u user-uuid] [-d] [-q]"
    parser = OptionParser( usage = usage )
    parser.add_option("-e", "--email",
                  dest="email",
                  help="Print the uuid(s) associated with the email and exit." )
    parser.add_option("-u", "--user",
                      dest="user_uuid",
                      help="The user uuid of the user to create the year in review summary for." )
    parser.add_option( "-y", "--year",
                       dest="year",
                       help="The YYYY year to create the summary for." )

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

    elif options.user_uuid:
        user_uuid = options.user_uuid

        if options.year:
            call_build_video_summary( user_uuid, int( options.year ) )
        else:
            print "ERROR: Must provide -y YYYY argument for year to summarize."
            sys.exit( 0 )

