#!/usr/bin/env python
#
# Video Processor front end server.
#
import web
web.config.debug = False

import json

# Application modules.  These modules contain
# the actual server endpoints and application
# logic
import dev
import processor
import media

# wsgilog will manage logging to the main server's
# log files over WSGI
import sys
from wsgilog import WsgiLog

# Our application config
from appconfig import AppConfig
try:
    config = AppConfig( 'popeye' ).config()
except Exception as e:
    print( str( e ) )
    sys.exit( 1 )

# Create a webpy session-like thing for SQLAlchemy,
# so the database session is available to all web 
# endpoints in web.ctx.orm.
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import *

"""
Someone who knows web.py and SQLAlchemy should review this
scoped_session() stuff and the code in base/models.py to
make sure I ain't doing something stupid/low performance
with this code.  I had a tough time getting it to
do what I needed (i.e. work!)
"""

conn = 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name
engine = create_engine( conn, pool_recycle=3600 )
SessionFactory = map( engine )
Session = scoped_session( SessionFactory )

def load_sqla( handler ):
    print( "Getting a new session...")
    web.ctx.orm = Session()
    web.ctx.SessionFactory = SessionFactory
    try:
        return handler()
    except web.HTTPError as e:
        web.ctx.log.debug( "Committing on HTTPError:" + str( e ) )
        web.ctx.orm.commit()
        raise
    except Exception as f:
        web.ctx.log.debug( "Rolling back on exception:" + str( f ) )
        web.ctx.orm.rollback()
        raise
    finally:
        web.ctx.log.debug( "Committing on request done" )
        web.ctx.orm.commit()
        web.ctx.orm.close()
        # If the above alone doesn't work, uncomment 
        # the following line:
        #web.ctx.orm.expunge_all() 

# Create a more convienent way to access the
# logger on the webpy context
def attach_logger( handler ):
    web.ctx.log = web.ctx.environ['wsgilog.logger']
    return handler()

# This bolts our application modules into
# the global endpoint name space.
#
urls = (
    '/dev', dev.dev_app,
    '/processor', processor.processor_app,
    '/media', media.media_app
)

# The WSGI Logger
class Log( WsgiLog ):
    def __init__( self, application ):
        print "Initializing WSGI Logger"
        WsgiLog.__init__(
            self,
            application,
            logformat = '%(name)-22s: %(module)-7s: %(lineno)-3s: %(funcName)-12s: %(asctime)s: %(levelname)-5s: %(message)s',
            loglevel = config.loglevel,
            logname = 'popeye',
            tostream = True,
            toprint = True,
            tofile = True,
            file = config.logfile
            )

if __name__ == "__main__":
    app = web.application( urls, globals() )
    app.add_processor( attach_logger )
    app.add_processor( load_sqla ) 
    app.run( Log )
else:
    app = web.application( urls, globals(), autoreload=False )
    app.add_processor( attach_logger )
    app.add_processor( load_sqla )
    application = app.wsgifunc( Log )
