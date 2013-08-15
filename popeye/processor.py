import web
import json;
import os
import threading

from worker import process_video
from facebook import sync, unsync

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
        thread = threading.Thread( target=sync, args=(data, web.ctx.orm, web.ctx.log) )
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
        thread = threading.Thread( target=unsync, args=(data, web.ctx.orm, web.ctx.log) )
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

        main_file = os.path.basename( data.path )
        dirname   = os.path.dirname( data.path )
        basename, ext = os.path.splitext( main_file )

        uuid = basename

        input_video = data.path
        input_info  = os.path.join( dirname, basename + '.json' )
        input_metadata = os.path.join( dirname, basename + '_metadata.json' )

        # Output file names
        output_video = os.path.join( dirname, basename + '.mp4' )
        output_thumbnail = os.path.join( dirname, basename + '_thumbnail.jpg' )
        output_poster = os.path.join( dirname, basename + '_poster.jpg' )
        output_metadata = input_metadata
        output_face = os.path.join( dirname, basename + '_face01.jpg' )

        res = {
            'uuid': uuid,
            'info': input_info,
            'video': {
                'input': input_video,
                'output': output_video
                },
            'thumbnail': {
                'input': output_video,
                'output': output_thumbnail
                },
            'poster': {
                'input': output_video,
                'output': output_poster
                },
            'metadata': {
                'input': input_metadata,
                'output': output_metadata
                },
            'face': {
                'input': output_video,
                'output': output_face
                }
            }

        # Go do the work.  This routine will "fork"
        # and return control immediately to here
        # so we can respond back to brewtus
        #
        # NOTE ... is this cool with web.ctx.orm?  Do
        # we need to worry about some sort of locking?
        #
        web.ctx.log.info( 'Starting a worker thread for ' + res['uuid'] )
        thread = threading.Thread( target=process_video, args=(res, web.ctx.orm, web.ctx.log) )
        thread.start()

        return json.dumps(res)

processor_app = web.application(urls, locals())
