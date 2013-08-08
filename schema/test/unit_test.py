import unittest
import datetime
from sqlalchemy import *
import sys

class SchemaTest( unittest.TestCase ):
    verbose = False

    username = 'video_dev_1'
    password = 'video_dev_1'
    database = 'video_dev_1'

    engine = create_engine( 'mysql+mysqldb://'
                            +username+':'+password
                            +'@testpub.c9azfz8yt9lz.us-west-2.rds.amazonaws.com:3306/'
                            +database, echo=verbose )

    meta = None
    conn = None

    users = None
    media = None
    media_assets = None
    media_asset_features = None
    media_comments = None
    contacts = None

    @classmethod
    def setUpClass( self ):
        try:
            print "Getting database connection."
            self.meta = MetaData()
            self.meta.reflect( bind=self.engine )
            self.conn = self.engine.connect()
        except:
            print "Failed to get database connection, aborting tests."
            raise

        try:
            print "Validating metadata import"
            self.users = self.meta.tables['users']
            self.media = self.meta.tables['media']
            self.media_assets = self.meta.tables['media_assets']
            self.media_asset_features = self.meta.tables['media_asset_features']
            self.media_comments = self.meta.tables['media_comments']
            self.contacts = self.meta.tables['contacts']

            print "Cleaning up any stale rows from prior tests."
            self.delete_test_rows()
        except:
            print "Something went wrong getting the database schema, aborting tests."
            raise


    @classmethod
    def tearDownClass( self ):
        try: 
            print "Testing delete of rows from the database."
            self.delete_test_rows()
        except:
            print "Something went wrong cleaning up test data - test data may be resident in the database."
            raise
        
        try:
            self.conn.close()
            self.engine.dispose()
        except:
            print "Something went wrong closing down database connection."
            raise


    @classmethod
    def delete_test_rows( self ):
        self.conn.execute( 
            self.media_assets.delete()
            .where( self.media_assets.c.filename == 'unit_test_insert' ) )
        self.conn.execute( 
            self.media_comments.delete()
            .where( self.media_comments.c.comment == 'unit_test_insert' ) )
        self.conn.execute( 
            self.contacts.delete()
            .where( self.contacts.c.contact_name == 'unit_test_insert' ) )
        self.conn.execute( 
            self.media.delete()
            .where( self.media.c.description == 'unit_test_insert' ) )
        self.conn.execute( 
            self.users.delete()
            .where( self.users.c.username == 'unit_test_insert' ) )

    def test_metadata( self ):
        def test_table( table_name ):
            self.assertIn( table_name, self.meta.tables, msg=table_name+' table not found in database' )

        try:
            print "Validating metadata."
            test_table( 'users' )
            test_table( 'media' )
            test_table( 'media_assets' )
            test_table( 'media_asset_features' )
            test_table( 'media_comments' )
            test_table( 'contacts' )

        except:
            print "ERROR during metadata validation."
            raise

    def insert_users_rows( self ):
        self.conn.execute( self.users.insert(),
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
                           created_date   = None,
                           updated_date   = None )

    def test_users_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to users table."
            self.insert_users_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.users.c.username == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in users, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to users."
            raise
        finally:
            trans.rollback()

    def insert_media_rows( self ):
        for result in self.conn.execute( select( [self.users.c.id] ).where( self.users.c.username == 'unit_test_insert' ) ):
            self.conn.execute( self.media.insert(), 
                               id             = None, # Populated by the database.
                               user_id        = result[0],
                               uuid           = 'unit_test_insert',
                               media_type     = 'original',
                               title          = 'unit_test_insert',
                               filename       = 'unit_test_insert',
                               description    = 'unit_test_insert',
                               recording_date = datetime.datetime.now(),
                               view_count     = 0,
                               lat            = 123.45,
                               lng            = 184.32,
                               created_date   = None,
                               updated_date   = None )

    def test_media_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to media table."
            self.insert_users_rows()
            self.insert_media_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.media.c.description == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in media, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to media."
            raise
        finally:
            trans.rollback()

    def insert_media_assets_rows( self ):
        for result in self.conn.execute( select( [self.media.c.id] ).where( self.media.c.description == 'unit_test_insert' ) ):
            self.conn.execute( self.media_assets.insert(), 
                               id             = None, # Populated by the database.
                               media_id       = result[0],
                               uuid           = 'unit_test_insert',
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

    def test_media_assets_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to media_assets table."
            self.insert_users_rows()
            self.insert_media_rows()
            self.insert_media_assets_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.media_assets.c.filename == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in media_assets, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to media_assets."
            raise
        finally:
            trans.rollback()

    def insert_media_comments_rows( self ):
        for media_id in self.conn.execute( select( [self.media.c.id] ).where( self.media.c.description == 'unit_test_insert' ) ):
            for user_id in self.conn.execute( select( [self.users.c.id] ).where( self.users.c.username == 'unit_test_insert' ) ):
                self.conn.execute( self.media_comments.insert(), 
                                   id             = None, # Populated by the database.
                                   media_id       = media_id[0],
                                   user_id        = user_id[0],
                                   uuid           = 'unit_test_insert',
                                   comment        = 'unit_test_insert',
                                   comment_number = 0,
                                   created_date   = None,
                                   updated_date   = None )

    def test_media_comments_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to media_comments table."
            self.insert_users_rows()
            self.insert_media_rows()
            self.insert_media_assets_rows()
            self.insert_media_comments_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.media_comments.c.comment == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in media_comments, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to media_comments."
            raise
        finally:
            trans.rollback()

    def insert_contacts_rows( self ):
        for user_id in self.conn.execute( select( [self.users.c.id] ).where( self.users.c.username == 'unit_test_insert' ) ):
            self.conn.execute( self.contacts.insert(), 
                               id                = None, # Populated by the database.
                               user_id           = user_id[0],
                               contact_name      = 'unit_test_insert',
                               contact_email     = 'unit_test_insert',
                               contact_viblio_id = user_id[0],
                               provider          = 'facebook',
                               provider_id       = 0,
                               created_date   = None,
                               updated_date   = None )

    def test_contacts_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to contacts table."
            self.insert_users_rows()
            self.insert_contacts_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.contacts.c.contact_name == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in contacts, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to contacts."
            raise
        finally:
            trans.rollback()

    def insert_media_asset_features_rows( self ):
        inserted_ids = []
        for media_asset_id in self.conn.execute( select( [self.media_assets.c.id] ).where( self.media_assets.c.filename == 'unit_test_insert' ) ):
            for contact_id in self.conn.execute( select( [self.contacts.c.id] ).where( self.contacts.c.contact_name == 'unit_test_insert' ) ):
                result = self.conn.execute( self.media_asset_features.insert(), 
                                            id             = None, # Populated by the database.
                                            media_asset_id = media_asset_id[0],
                                            feature_type   = 'face',
                                            coordinates    = 'unit_test_insert',
                                            contact_id     = contact_id[0],
                                            created_date   = None,
                                            updated_date   = None )
                inserted_ids.append( result.inserted_primary_key[0] )
        return inserted_ids
                
    def delete_media_asset_features_rows( self, inserted_ids ):
        for inserted_id in inserted_ids:
            self.conn.execute( 
                self.media_asset_features.delete()
                .where( self.media_asset_features.c.id == inserted_id ) )

    def test_media_asset_features_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to media_asset_features table."
            self.insert_users_rows()
            self.insert_contacts_rows()
            self.insert_media_rows()
            self.insert_media_assets_rows()
            inserted_ids = self.insert_media_asset_features_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.media_asset_features.c.id.in_( inserted_ids ) ) ).fetchone()[0]
            self.assertEquals( rows, 1, msg="There should have been 1 matching row in media_asset_features, instead there were "+str( rows ) )

            self.delete_media_asset_features_rows( inserted_ids )

        except:
            print "Something went wrong testing inserts to media_asset_features."
            raise
        finally:
            trans.rollback()

if __name__ == '__main__':
    unittest.main()

