import json
import os
import uuid

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import scoped_session, sessionmaker

from vib.db.models import *

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

conn = 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name
engine = create_engine( conn, pool_recycle=3600 )
SessionFactory = db_map( engine )
Session = scoped_session( SessionFactory )

def valid_session( sess ):
    try:
        q = sess.execute( 'select 1;' )
        if q.rowcount:
            return True
        else:
            raise Exception( "DB Connection Error." )
    except Exception as e:
        return False

def get_session():
    sess = Session()
    if valid_session( sess ):
        print "Session is valid"
        return sess
    else:
        print "Invalid session, issuing rollback"
        sess.rollback()
        return sess
