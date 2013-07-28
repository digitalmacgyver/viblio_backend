#!/usr/bin/env python
#
# Video Processor front end server.
#
import web
import json;

# Application modules
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

if __name__ == "__main__":
    app.run(Log)

