import web
import json;

urls = (
    '/ping', 'ping',
    '/error/(.+)', 'error'
    )

# /test/ping?args
#
# Simple ping endpoint.  Sends the query back as a JSON
# document.  Can use to make sure the server is running and
# is nominally functional.
#
class ping:
    def GET(self):
        data = web.input()
        web.header('Content-Type', 'application/json')
        return json.dumps(data)

# /error/<type>
#
# Test error handling and logging
#
class error:
    def GET(self, etype):

        # Grab query params
        data = web.input()

        # Prepare response headers
        web.header('Content-Type', 'application/json')

        if etype == 'stdout':
            # STDOUT is logged to the application log file as DEBUG
            print 'Error: etype is: %s' % etype
            return json.dumps(data)

        elif etype == 'exception':
            # This is how you should handle normal application
            # errors.  The response back is a 200, with a JSON
            # struct that looks like { error: True, message: error-message }
            try:
                raise Exception( 'bummer' );
            except Exception, e:
                return json.dumps({'error': True, 'message': str(e)})
                

dev_app = web.application(urls, locals())
