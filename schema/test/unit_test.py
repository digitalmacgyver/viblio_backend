import unittest
import datetime
from sqlalchemy import *
import sys

class SchemaTest( unittest.TestCase ):
    verbose = False

    username = 'video_dev'
    password = 'video_dev'
    database = 'video_dev'

    engine = create_engine( 'mysql+mysqldb://'
                            +username+':'+password
                            +'@videos.c9azfz8yt9lz.us-west-2.rds.amazonaws.com:3306/'
                            +database, echo=verbose )

    meta = None
    conn = None

    detector = None
    image = None
    image_label = None
    video = None
    video_label = None
    
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
            self.video = self.meta.tables['video']
            self.video_encoding = self.meta.tables['video_encoding']
            self.image = self.meta.tables['image']

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
            self.image.delete()
            .where( self.image.c.format == 'unit_test_insert' ) )
        self.conn.execute( 
            self.video_encoding.delete()
            .where( self.video_encoding.c.format == 'unit_test_insert' ) )
        self.conn.execute( 
            self.video.delete()
            .where( self.video.c.description == 'unit_test_insert' ) )

    def test_metadata( self ):
        def test_table( table_name ):
            self.assertIn( table_name, self.meta.tables, msg=table_name+' table not found in database' )

        try:
            print "Validating metadata."
            test_table( 'video' )
            test_table( 'video_encoding' )
            test_table( 'image' )
        except:
            print "ERROR during metadata validation."
            raise

    def insert_video_rows( self ):
        ins = self.video.insert()
        # id of None because of auto sequencing of the ID.
        self.conn.execute( ins, 
                           id=None, # Populated by the database.
                           owner_id = 23,
                           title='unit_test_insert',
                           filename='C:\User\Desktop\Movie.mpg',
                           description='unit_test_insert',
                           lat=120.00432,
                           lng=233.001233,
                           recording_date=datetime.datetime.now() );
        
        # Bulk insert a few more rows.
        self.conn.execute( self.video.insert(), [
                { 'description' : 'unit_test_insert' },
                { 'description' : 'unit_test_insert' },
                ] )


    def test_video_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion to video table."
            self.insert_video_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.video.c.description == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 3, msg="There should have been 3 matching rows in video, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to video."
            raise
        finally:
            trans.rollback()

    def insert_video_encoding_rows( self ):
        for result in self.conn.execute( select( [self.video.c.id] ).where( self.video.c.description == 'unit_test_insert' ) ):
            self.conn.execute( self.video_encoding.insert(),
                               id=None,
                               video_id=result[0],
                               url="http://s3/video-name.mp4",
                               metadata_url="http://s3/video-name.json",
                               format='unit_test_insert',
                               type='MP4',
                               hash='A523B30432934590012E',
                               lenth=2202.23,
                               width=720,
                               height=480 );


    def test_video_encoding_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion into video_encoding table."
            # Add a few video labels.
            self.insert_video_rows()
            self.insert_video_encoding_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.video_encoding.c.format == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 3, msg="There should have been 3 matching rows in video_encoding, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to video_label."
            raise
        finally:
            trans.rollback()

    def insert_image_rows( self ):
        for ids in self.conn.execute( select( [self.video_encoding.c.id, self.video_encoding.c.video_id ] ).where( self.video_encoding.c.format == 'unit_test_insert' ) ):
            print "Adding image for video encoding:", ids[0]

            self.conn.execute( self.image.insert(),
                               id=None,
                               video_encoding_id=ids[0],
                               video_id=ids[1],
                               time_stamp=33.004999,
                               url='http://s3/video/0000123.jpg',
                               metadata_url='http://s3/video/0000123.json',
                               format='unit_test_insert',
                               width=1024,
                               height=768 )

    def test_image_insert( self ):
        trans = self.conn.begin()
        try:
            print "Testing insertion into image table."
            # Add a few images.
            self.insert_video_rows()
            self.insert_video_encoding_rows()
            self.insert_image_rows()

            # Run a select and get back the right number of rows.
            rows = self.conn.execute( select( [ func.count() ] ).where( self.image.c.format == 'unit_test_insert' ) ).fetchone()[0]
            self.assertEquals( rows, 3, msg="There should have been 3 matching rows in image, instead there were "+str( rows ) )

        except:
            print "Something went wrong testing inserts to image."
            raise
        finally:
            trans.rollback()

if __name__ == '__main__':
    unittest.main()

