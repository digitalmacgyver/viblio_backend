#!/usr/bin/python

import datetime
from sqlalchemy import *

# Set up connection information.

verbose = False

username = 'video_dev'
password = 'video_dev'
database = 'video_dev'

# Connect to the database.
print "Creating SQLAlchemy engine for:", database
engine = create_engine( 'mysql+mysqldb://'
                        +username+':'+password
                        +'@videos.c9azfz8yt9lz.us-west-2.rds.amazonaws.com:3306/'
                        +database, echo=verbose )

# Extract schema inforation from the database.
print "Generating SQLAlchemy data structures from the database schema."
meta = MetaData()
meta.reflect( bind=engine )

for table in meta.tables:
    print "Found table:", table

video = meta.tables['video']
video_encoding = meta.tables['video_encoding']
image = meta.tables['image']

# Get a connection to issue SQL with.
print "Creating a database connection."
conn = engine.connect()

# Create a metadata structure appropriate for insert statements to the
# video table.
ins = video.insert()

# Perform a single row insert by assigning column names to values.
print "Inserting a row into the video table."
result = conn.execute( ins, 
                       id=None, # Populated by the database.
                       owner_id = 23,
                       title='unit_test_insert',
                       filename='C:\User\Desktop\Movie.mpg',
                       description='unit_test_insert',
                       lat=120.00432,
                       lng=233.001233,
                       recording_date=datetime.datetime.now() );

# Get the id number of the recently inserted row. 
# 
# Note, this technique is only availbale for single row inserts.
print "Inserted video id was:", result.inserted_primary_key

# Perform a batch insert that adds many rows at one time.
#
# Illustrate the "returning()" method of getting data back from the
# database about our insert.
#
# Note 1: all rows must have the same columns.
# Note 2: Any columns not defined will recieve default values.
print "Inserting multiple rows into the video table."
result = conn.execute( video.insert(),
                       [
        { 'description' : 'unit_test_insert', 'lat' : 220.4, 'lng' : 2.123 },
        { 'description' : 'unit_test_insert', 'lat' : 110.2, 'lng' : 321.132 },
        # Note, we can have as many rows as we want here.
        ] )
# Further note - unlike the one by one rows above you can't get the
# IDs of rows inserted in this way.

print "Updating a row in the video table."
result = conn.execute( video.update().where( video.c.lat == 220.4 ).values( lat=330.6 ) );

# Add a video_encoding for each video.  Note that we must provide a
# video_id that matches an Id found in the video table when adding
# these rows.
#
# Begin by getting a list of videos in the video table.
for videoId in conn.execute( 
    select( [video.c.id] )
    .where( video.c.description == 'unit_test_insert' ) ):
    # Then for each video, add a child row in the video_encoding_insert table.
    print "Adding a video_encoding row associated with video id:", videoId[0]
    result = conn.execute( video_encoding.insert(),
                                id=None,
                                video_id=videoId[0],
                                url="http://s3/video-name.mp4",
                                metadata_url="http://s3/video-name.json",
                                format='unit_test_insert',
                                type='MP4',
                                hash='A523B30432934590012E',
                                lenth=2202.23,
                                width=720,
                                height=480 );
    print "Inserted video_encoding had id:", result.inserted_primary_key[0]
    result.close()

        
for ids in conn.execute( 
    select( [video_encoding.c.id, video_encoding.c.video_id ] )
    .where( video_encoding.c.format == 'unit_test_insert' ) ):
    print "Adding image for video encoding:", ids[0]

    conn.execute( image.insert(),
                       id=None,
                       video_encoding_id=ids[0],
                       video_id=ids[1],
                       time_stamp=33.004999,
                       url='http://s3/video/0000123.jpg',
                       metadata_url='http://s3/video/0000123.json',
                       format='unit_test_insert',
                       width=1024,
                       height=768 )

# Clean up our tests.
print "Deleting rows from image."
conn.execute( 
    image.delete()
    .where( image.c.format == 'unit_test_insert' ) )

print "Deleting rows from video_encoding."
conn.execute( 
    video_encoding.delete()
    .where( video_encoding.c.format == 'unit_test_insert' ) )

print "Deleting rows from video."
conn.execute( 
    video.delete()
    .where( video.c.description == 'unit_test_insert' ) )

# Close our connections.
print "Closing database connection."
conn.close()
print "Releasing database engine."
engine.dispose()
