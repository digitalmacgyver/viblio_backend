import web
import json;
import os

from config import Config
config = Config( 'popeye.cfg' )

urls = (
    '/process', 'process',
)

# Brewtus has successfully uploaded a new file
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

        input_video = data.path
        input_info  = os.path.join( dirname, basename + '.json' )
        input_metadata = os.path.join( dirname, basename + '_metadata.json' )

        # Make sure all input files are present

        # Output file names
        output_video = os.path.join( dirname, basename + '.mp4' )
        output_thumbnail = os.path.join( dirname, basename + '_thumbnail.jpg' )
        output_poster = os.path.join( dirname, basename + '_poster.jpg' )
        output_metadata = input_metadata

        # Run the processors
        
        res = {
            'video': output_video,
            'thumbnail': output_thumbnail,
            'poster': output_poster,
            'metadata': output_metadata
            }

        return json.dumps(res)

worker_app = web.application(urls, locals())
