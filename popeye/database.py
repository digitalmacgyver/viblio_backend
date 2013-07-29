from config import Config
config = Config( 'popeye.cfg' )

import datetime
from sqlalchemy import *

class DB:
    def __init__( self ):
        conns = 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name
        self.conn = None
        try:
            self.engine = create_engine( conns, echo=config.db_verbose )
            self.meta = MetaData()
            self.meta.reflect( bind=self.engine )
        except Exception, e:
            raise Exception( e.message )

    def conn(self):
        if not self.conn:
            try:
                self.conn = self.engine.connect()
            except Exception, e:
                raise Exception( e.message )
        return self.conn
