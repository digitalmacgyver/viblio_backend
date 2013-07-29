import web
import json;
import os
import threading

from processor import process_video

from config import Config
config = Config( 'popeye.cfg' )

urls = (
    '/process', 'process',
)

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
                }
            }

        # Go do the work.  This routine will "fork"
        # and return control immediately to here
        # so we can respond back to brewtus
        #
        # data = process_video( res, web.ctx.orm )

        thread = threading.Thread( target=process_video, args=(res, web.ctx.orm) )
        thread.start()

        return json.dumps(res)

worker_app = web.application(urls, locals())
