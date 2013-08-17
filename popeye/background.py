"""
This is the base class for any/all background tasks that will perform
database operations.  It exists to properly close down the ORM session
when it is finished with.
"""
class Background:
    # Subclasses must override this method
    def run():
        pass

    def __init__( self, orm, log, data ):
        self.orm = orm
        self.log = log
        self.data = data

    def start( self ):
        try:
            self.run()
        except:
            self.log.debug( "Rolling back DB on exception" )
            self.orm.rollback()
            self.orm.close()
            raise
        finally:
            self.log.debug( "Committing on background task done" )
            self.orm.commit()
            self.orm.close()
