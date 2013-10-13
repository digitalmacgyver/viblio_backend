"""
This is the base class for any/all background tasks that will perform
database operations.  It exists to properly close down the ORM session
when it is finished with.
"""
from appconfig import AppConfig
try:
    config = AppConfig( 'popeye' ).config()
except Exception, e:
    print( str(e) )
    sys.exit(1)

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import *

import threading

class Background(object):
    # Subclasses must override this method
    def run():
        pass

    def __init__( self, SessionFactory, log, data ):
        self.SessionFactory = SessionFactory
        self.log = log
        self.data = data

    def start( self ):
        try:
            self.log.info( "Creating a DB session for thread: " + str( threading.current_thread().name ) )
            Session = scoped_session( self.SessionFactory )
            self.orm = Session()

            self.run()
        except Exception as e:
            self.log.error( "Rolling back DB on exception: %s" % str(e)  )
            self.orm.rollback()
            self.orm.close()
            raise
        finally:
            self.log.info( "Committing on background task done" )
            self.orm.commit()
            self.orm.close()
