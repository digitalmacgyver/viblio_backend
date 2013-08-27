import web
import json;
import os
import threading

from worker   import Worker
from facebook import FacebookSync, FacebookUnsync

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

urls = (
    '/process', 'process',
    '/facebook', 'fbsync',
    '/unfacebook', 'fbunsync'
)

# Incoming request from Cat server to get facebook data
#
class fbsync:
    def GET(self):
        # Get input params
        data = web.input()

        # Prepare response
        web.header('Content-Type', 'application/json')

        if not 'uid' in data:
            return json.dumps({'error': True, 'message': 'Missing uid param'})

        if not 'access_token' in data:
            return json.dumps({'error': True, 'message': 'Missing access_token param'})

        if not 'id' in data:
            return json.dumps({'error': True, 'message': 'Missing id param'})

        web.ctx.log.info( 'Starting a facebook sync thread for ' + data['uid'] )

        fb = FacebookSync( web.ctx.SessionFactory, web.ctx.log, data )
        thread = threading.Thread( target=fb.start )
        thread.start()

        return json.dumps({})

# Incoming request from Cat server to remove facebook data
#
class fbunsync:
    def GET(self):
        # Get input params
        data = web.input()

        # Prepare response
        web.header('Content-Type', 'application/json')

        if not 'uid' in data:
            return json.dumps({'error': True, 'message': 'Missing uid param'})

        if not 'access_token' in data:
            return json.dumps({'error': True, 'message': 'Missing access_token param'})

        if not 'id' in data:
            return json.dumps({'error': True, 'message': 'Missing id param'})

        web.ctx.log.info( 'Starting a facebook un-sync thread for ' + data['uid'] )

        fb = FacebookUnsync( web.ctx.SessionFactory, web.ctx.log, data )
        thread = threading.Thread( target=fb.start )
        thread.start()

        return json.dumps({})

# Brewtus has successfully uploaded a new file.  It will
# call this endpoint with path=xxx where xxx is the full
# pathname/filename of the uploaded file.  From this
# information, everything else will be guessed.
#
class process:
    def GET(self):
        # Get input params
        data = web.input()

        # Prepare response
        web.header('Content-Type', 'application/json')

        if not 'path' in data:
            return json.dumps({'error': True, 'message': 'Missing path param'})
        res = {'full_filename': data.path}

        # Go do the work.  This routine will "fork"
        # and return control immediately to here
        # so we can respond back to brewtus
        #
        # NOTE ... is this cool with web.ctx.orm?  Do
        # we need to worry about some sort of locking?
        #
        web.ctx.log.info( 'Starting a worker thread for ' + res['full_filename'] )

        wrk = Worker( web.ctx.SessionFactory, web.ctx.log, res )
        thread = threading.Thread( target=wrk.start )
        thread.start()

        return json.dumps(res)

processor_app = web.application(urls, locals())
