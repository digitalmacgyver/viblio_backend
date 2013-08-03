"""
Media information endpoints
"""
import web
import json;

from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

from models import *
from sqlalchemy import desc

import boto
from boto.s3.key import Key

urls = (
    '/get', 'get',
    '/delete', 'delete'
)

"""
/media/get?uid=user-uuid[&mid=mediafile-uuid]

Requires a user uuid.  If that is the only option supplied,
returns a array of all media for this user.

Can optionally supply a mediafile uuid.  If that is supplied,
then return only that mediafile if it is owned by the user
indicated by the user uuid.

"""
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
        mid = None
        if 'mid' in data:
            mid = data.mid

        # Do the database query
        result = None
        if not mid:
            result = web.ctx.orm.query( Video ).filter_by( user_id = uid ).order_by( Video.id.desc() )
        else:
            result = web.ctx.orm.query( Video ).filter_by( user_id = uid, uuid = mid ).first()

        if not result:
            return json.dumps({'error':True, 'message':'Mediafile not found for %s' % mid})

        if not mid:
            # map the result into a array of serializable objects
            a = map( lambda mf: mf.to_serializable_dict(), result )
            # Return the JSON, USING THE CORRECT DECODER!!
            return json.dumps({ 'media': a}, cls=SWEncoder, indent=2)
        else:
            return result.toJSON()

class delete:
    def GET(self):
        # Get input params
        data = web.input()

        # Prepare response
        web.header('Content-Type', 'application/json')
        res = {}

        if not 'uid' in data:
            return json.dumps({'error': True, 'message': 'Missing uid param'})
        uid = data.uid
        
        if not 'mid' in data:
            return json.dumps({'error': True, 'message': 'Missing mid param'})
        mid = data.mid
        
        # Do the database query
        result = web.ctx.orm.query( Video ).filter_by( user_id = uid, uuid = mid ).first()

        if not result:
            return json.dumps({'error':True, 'message':'Mediafile not found for %s' % mid})

        # Delete it from S3
        try:
            s3 = boto.connect_s3(config.awsAccess, config.awsSecret)
            bucket = s3.get_bucket(config.bucket_name)
        except Exception, e:
            return json.dumps({'error':True, 'message': 'Failed to obtain s3 bucket: %s' % e.message})

        try:
            for key in bucket.list( prefix=mid ):
                key.delete()
        except Exception, e:
            return json.dumps({'error':True, 'message': 'Failed to delete from bucket: %s' % e.message})

        # Now the database record delete
        try:
            web.ctx.orm.delete( result )
        except Exception, e:
            return json.dumps({'error':True, 'message': 'Failed to delete from ORMt: %s' % e.message})

        return json.dumps({})

media_app = web.application(urls, locals())
