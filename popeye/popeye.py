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
import worker
import media

# wsgilog will manage logging to the main server's
# log files over WSGI
import sys, logging
from wsgilog import WsgiLog

# Our application config
from config import Config
config = Config( 'popeye.cfg' )

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

# This bolts our application modules into
# the global endpoint name space.
#
urls = (
    '/dev', dev.dev_app,
    '/processor', worker.worker_app,
    '/media', media.media_app
)

# The WSGI Logger
class Log(WsgiLog):
    def __init__(self, application):
        WsgiLog.__init__(
            self,
            application,
            logformat = '%(asctime)s %(levelname)-4s %(message)s',
            loglevel = logging.DEBUG,
            tostream = True,
            tofile = True,
            toprint = True,
            file = config.log_file,
            tohtml = False
            )

app = web.application(urls, locals())
app.add_processor( load_sqla )

if __name__ == "__main__":
    app.run(Log)

