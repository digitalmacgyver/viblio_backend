"""
Media information endpoints
"""
import web
import json;

import datetime
from sqlalchemy import *

from config import Config
config = Config( 'popeye.cfg' )

conn = 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name
print conn
engine = create_engine( conn, echo=config.db_verbose )

print "Generating SQLAlchemy data structures from the database schema."
meta = MetaData()
meta.reflect( bind=engine )

for table in meta.tables:
    print "Found table:", table


urls = (
    '/get', 'get',
)

class get:
    def GET(self):
        # Get input params
        data = web.input()

        # Prepare response
        web.header('Content-Type', 'application/json')
        res = {}

        if not 'uid' in data:
            return json.dumps({'error': True, 'message': 'Missing uid param'})
        uid = data.uid
        
        # If mid is present, we're fetching a single mediafile
        if 'mid' in data:
            mid = data.mid

        return json.dumps(res)

media_app = web.application(urls, locals())
