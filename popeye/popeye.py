#!/usr/bin/env python
#
# Video Processor front end server.
#
import web
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
except Exception, e:
    print( str(e) )
    sys.exit(1)

# Create a webpy session-like thing for SQLAlchemy,
# so the database session is available to all web 
# endpoints in web.ctx.orm.
from sqlalchemy.orm import scoped_session, sessionmaker
from models import *
def load_sqla(handler):
    web.ctx.orm = scoped_session(sessionmaker(bind=engine))
    try:
        return handler()
    except web.HTTPError:
       web.ctx.orm.commit()
       raise
    except:
        web.ctx.orm.rollback()
        raise
    finally:
        web.ctx.orm.commit()
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
class Log(WsgiLog):
    def __init__(self, application):
        WsgiLog.__init__(
            self,
            application,
            logformat = '%(name)s: %(asctime)s %(levelname)-4s %(message)s',
            loglevel = config.loglevel,
            logname = 'popeye',
            tostream = True,
            tofile = True,
            toprint = True,
            file = config.logfile
            )

"""
app = web.application(urls, locals())
app.add_processor( load_sqla )

if __name__ == "__main__":
    app.run(Log)
"""
if __name__ == "__main__":
    app = web.application(urls, globals())
    app.add_processor( attach_logger )
    app.add_processor( load_sqla ) 
    app.run(Log)
else:
    app = web.application(urls, globals(), autoreload=False)
    app.add_processor( attach_logger )
    app.add_processor( load_sqla )
    application = app.wsgifunc(Log)

