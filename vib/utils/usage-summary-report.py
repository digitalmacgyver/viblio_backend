#!/usr/bin/env python

'''Simple report to send out emails about our usage over the last few months.'''

import copy
import csv
import datetime
import mandrill
from sqlalchemy import and_, not_

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

import vib.utils.s3 as s3
import vib.db.orm
from vib.db.models import *

orm = vib.db.orm.get_session()

'''

month	new users	# users who uploaded	GB videos uploaded	# users who shared individual videos	# individual videos shared	# users who shared albums	# albums shared

Monthly reporting stats of:

* New users

select count( * ), date_format( created_date, "%Y-%m" ) from users group by 2 order by created_date desc;

* # of users who uploaded

select count( distinct( user_id ) ), date_format( created_date, "%Y-%m" ) from media where media_type = 'original' and not is_viblio_created group by 2 order by created_date desc;

* GB of videos uploaded

select sum( bytes ) / 1024 / 1024 / 1024, date_format( media_assets.created_date, "%Y-%m" ) from media, media_assets where media.id = media_id and media_type = 'original' and asset_type = 'original' and not is_viblio_created group by 2 order by media_assets.created_date desc;

* # of users who shared individual videos

select count( distinct( user_id ) ), date_format( created_date, "%Y-%m" ) from media_shares group by 2 order by created_date desc;

* # individual videos shared

select count( * ), date_format( created_date, "%Y-%m" ) from media_shares group by 2 order by created_date desc;

* # of users who shared albums

select count( distinct( user_id ) ), date_format( created_date, "%Y-%m" ) from communities group by 2 order by created_date desc;
 
* # of album shares

select count( * ), date_format( created_date, "%Y-%m" ) from communities group by 2 order by created_date desc;

==

CHECK IF WE CAN NOW REPORT OFF OF # OF SHARED VIDEO WATCHES BASED ON MIXPANEL NOW THAT WE HAVE IOS STATS.
TOTAL VIDEO VIEWS

'''

def compute_report():

    # Dictionary keyed off YYYY-MM, within which there is a dictionary
    # of stats.
    no_data = {
        'new_user_count' : 0,
        'upload_user_count' : 0,
        'upload_count' : 0,
        'upload_gb' : 0,
        'video_share_user_count' : 0,
        'video_share_count' : 0,
        'album_share_user_count' : 0,
        'album_share_count' : 0
    }
    stats_by_month = {}

    users = orm.query( Users ).all()

    for user in users:
        month = user.created_date.strftime( "%Y-%m" )
        if month not in stats_by_month:
            stats_by_month[month] = copy.deepcopy( no_data )

        stats_by_month[month]['new_user_count'] += 1

    video_uploads = orm.query( Media, MediaAssets ).filter( and_( Media.id == MediaAssets.media_id, Media.media_type == 'original', MediaAssets.asset_type == 'original', Media.is_viblio_created == False ) ).all()
    user_monthly_stats = {}
    for video in video_uploads:
        media = video[0]
        asset = video[1]
        month = media.created_date.strftime( "%Y-%m" )
        if month not in stats_by_month:
            stats_by_month[month] = copy.deepcopy( no_data )
        if month not in user_monthly_stats:
            user_monthly_stats[month] = {}
        
        stats_by_month[month]['upload_count'] += 1
        stats_by_month[month]['upload_gb'] += float( asset.bytes ) / 1024 / 1024 / 1024

        if media.user_id not in user_monthly_stats[month]:
            user_monthly_stats[month][media.user_id] = True
            stats_by_month[month]['upload_user_count'] += 1

    video_shares = orm.query( MediaShares ).all()
    user_monthly_stats = {}    
    for video_share in video_shares:
        month = video_share.created_date.strftime( "%Y-%m" )
        if month not in stats_by_month:
            stats_by_month[month] = copy.deepcopy( no_data )
        if month not in user_monthly_stats:
            user_monthly_stats[month] = {}

        stats_by_month[month]['video_share_count'] += 1
        
        if video_share.user_id not in user_monthly_stats[month]:
            user_monthly_stats[month][video_share.user_id] = True
            stats_by_month[month]['video_share_user_count'] += 1

    album_shares = orm.query( Communities ).all()
    user_monthly_stats = {}
    for album_share in album_shares:
        month = album_share.created_date.strftime( "%Y-%m" )
        if month not in stats_by_month:
            stats_by_month[month] = copy.deepcopy( no_data )
        if month not in user_monthly_stats:
            user_monthly_stats[month] = {}

        stats_by_month[month]['album_share_count'] += 1
        
        if album_share.user_id not in user_monthly_stats[month]:
            user_monthly_stats[month][album_share.user_id] = True
            stats_by_month[month]['album_share_user_count'] += 1

    return stats_by_month

stats_by_month = compute_report()

subject = "Monthly VIBLIO Metrics"

report_columns = [ 'new_user_count',
                   'upload_user_count',
                   'upload_count',
                   'upload_gb',
                   'video_share_user_count',
                   'video_share_count',
                   'album_share_user_count',
                   'album_share_count' ]

message_top = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd" >
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />

        <title>%s</title>
   </head>
   <body>
     <p>Monthly VIBLIO Metrics Report</p>
''' % ( subject )

message_bottom = "  </body>\n</html>"

message = '''    <table border="1px">
      <tr>
'''

message += "        <th>Month</th>\n"

for column in report_columns:
    message += "        <th>%s</th>\n" % ( column )

message += "      </tr>\n"

for month in sorted( stats_by_month.keys(), reverse=True):
    data = stats_by_month[month]
    
    message += "<tr>\n"
    message += "        <td>%s</td>\n" % ( month )

    for column in report_columns:
        message += "        <td>%s</td>\n" % ( data.get( column, '' ) )

    message += "      </tr>\n"

mail = mandrill.Mandrill( config.mandrill_api_key )

envelope = {
    'auto_html'  : True,
    'auto_text'  : True,
    'from_email' : 'admin@viblio.com',
    'from_name'  : 'VIBLIO Admin',
    'subject'    : subject,
    'html'       : message_top + message + message_bottom,
    'to'         : [ { 'email' : 'matt@viblio.com', 'name' : 'Matthew Hayward', 'type' : 'to' } ],
    }

result = mail.messages.send( message=envelope )

print "Result of mail send was: %s" % ( result )





'''
with open( 'output.csv', 'wb' ) as csvfile:
    out = csv.writer( csvfile, quoting=csv.QUOTE_MINIMAL )
    out.writerow( ['media_id', 'track_id', 'image_url', 'detection_result' ] )

    for bad_image in bad_images:
        out.writerow( [ str( bad_image.media_id ), str( bad_image.track_id ), config.ImageServer + bad_image.uri, bad_image.coordinates ] )
'''

