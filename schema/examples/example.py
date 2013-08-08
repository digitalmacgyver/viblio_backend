#!/usr/bin/python

import datetime
from sqlalchemy import *

# Set up connection information.

verbose = False

username = 'video_dev_1'
password = 'video_dev_1'
database = 'video_dev_1'

db_server = '@testpub.c9azfz8yt9lz.us-west-2.rds.amazonaws.com:3306/'

# Connect to the database.
print "Creating SQLAlchemy engine for:", database
engine = create_engine( 'mysql+mysqldb://'
                        +username+':'+password
                        +db_server
                        +database, echo=verbose )

# Extract schema inforation from the database.
print "Generating SQLAlchemy data structures from the database schema."
meta = MetaData()
meta.reflect( bind=engine )

for table in meta.tables:
    print "Found table:", table

users = meta.tables['users']
media = meta.tables['media']
media_assets = meta.tables['media_assets']
media_asset_features = meta.tables['media_asset_features']
media_comments = meta.tables['media_comments']
contacts = meta.tables['contacts']

# Get a connection to issue SQL with.
print "Creating a database connection."
conn = engine.connect()

# Create a metadata structure appropriate for insert statements to the
# users table.
ins = users.insert()

# Perform a single row insert by assigning column names to values.
print "Inserting a row into the users table."
result = conn.execute( ins,
                       id             = None, # Populated by the database.
                       uuid           = 'unit_test_insert',
                       provider       = 'local',
                       provider_id    = 0,
                       username       = 'unit_test_insert',
                       password       = 'unit_test_insert',
                       email          = 'unit_test_insert',
                       displayname    = 'unit_test_insert',
                       active         = 'unit_test_insert',
                       accepted_terms = True,
                       # created_date and updated_date are populated
                       # by database triggers.  In fact, we don't need
                       # to include them here at all.
                       created_date   = None,
                       updated_date   = None )

# Get the id number of the recently inserted row. 
# 
# Note, this technique is only availbale for single row inserts.
print "Inserted user id was:", result.inserted_primary_key[0]

# Perform a batch insert that adds many rows at one time.
#
# Note 1: all rows must have the same columns.
# Note 2: Any columns not defined will recieve default values.
print "Inserting multiple rows into the users table."
result = conn.execute( users.insert(),
                       [
        { 'username' : 'unit_test_insert', 'uuid' : 'user2' },
        { 'username' : 'unit_test_insert', 'uuid' : 'user3' },
        # Note, we can have as many rows as we want here.
        ] )
# Further note - unlike the one by one rows above you can't get the
# IDs of rows inserted in this way.

print "Updating a row in the users table."
result = conn.execute( users.update().where( users.c.uuid == 'user2' ).values( active = 'yes' ) );

# Add some media for each user.  Note that we must provide a
# user_id that matches an id found in the users table when adding
# these rows.
#
# Begin by getting a list of users in the users table.
for user_id in conn.execute( 
    select( [users.c.id] )
    .where( users.c.username == 'unit_test_insert' ) ):
    # Then for each user, add a child row in the media table.
    print "Adding a media row associated with user id:", user_id[0]
    result = conn.execute( media.insert(), 
                           id             = None, # Populated by the database.
                           user_id        = user_id[0],
                           uuid           = 'unit_test_insert' + str( user_id[0] ),
                           media_type     = 'original',
                           title          = 'unit_test_insert',
                           filename       = 'unit_test_insert',
                           description    = 'unit_test_insert',
                           recording_date = datetime.datetime.now(),
                           view_count     = 0,
                           lat            = 123.45,
                           lng            = 184.32 )
    # NOTE: We can omit most columns that are not required.
    # created_date   = None,
    # updated_date   = None )

    media_id = result.inserted_primary_key[0]

    print "Inserted media had id:", media_id
    result.close()

    # Add an asset for the media we just added.
    print "Adding asset for media:", media_id
    
    conn.execute( media_assets.insert(), 
                  id             = None, # Populated by the database.
                  media_id       = media_id,
                  uuid           = 'unit_test_insert' + str( media_id ),
                  asset_type     = 'thumbnail',
                  mimetype       = 'unit_test_insert',
                  filename       = 'unit_test_insert',
                  uri            = 'unit_test_insert',
                  location       = 'unit_test_insert',
                  bytes          = 0,
                  width          = 0,
                  height         = 0,
                  time_stamp     = 120.343,
                  metadata_uri   = 'unit_test_insert',
                  provider       = 'facebook',
                  provider_id    = 'unit_test_insert',
                  view_count     = 0,
                  created_date   = None,
                  updated_date   = None )

# We could go on to insert rows for media_comments,
# media_asset_features, and contacts.

# Clean up our tests.
print "Deleting rows from media_assets."
conn.execute( 
    media_assets.delete()
    .where( media_assets.c.filename == 'unit_test_insert' ) )

print "Deleting rows from media."
conn.execute( 
    media.delete()
    .where( media.c.description == 'unit_test_insert' ) )

print "Deleting rows from users."
conn.execute( 
    users.delete()
    .where( users.c.username == 'unit_test_insert' ) )

# Close our connections.
print "Closing database connection."
conn.close()
print "Releasing database engine."
engine.dispose()
