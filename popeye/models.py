"""
Our data models.  For each table in the database, there is a corresponding
model specified here in this file.  These models are used by the application code in
database operations.  See http://docs.sqlalchemy.org/en/rel_0_8/orm/tutorial.html.

"""
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Numeric, DateTime
import datetime
import json

# Application config
from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

# Create the database engine
engine = create_engine( 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name )

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

""" JSON Serialize Stuff

Usage:

result = web.ctx.orm.query( Video ).first()
if result:
    print result.toJSON()

results = web.ctx.orm.query( Video ).all()
serializable_array = map( lambda mf: mf.to_serializable_dict(), results )
print json.dumps({ 'media': serializable_array}, cls=SWEncoder, indent=2)

"""
class Serializer(object):
    __public__ = None
    "Must be implemented by implementors"

    def to_serializable_dict(self):
        dict = {}
        for public_key in self.__public__:
            value = getattr(self, public_key)
            if value:
                dict[public_key] = value
        return dict

class SWEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Serializer):
            return obj.to_serializable_dict()
        if isinstance(obj, (datetime.datetime)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def SWJsonify(*args, **kwargs):
    return json.dumps(dict(*args, **kwargs), cls=SWEncoder, indent=2)
    # stolen from https://github.com/mitsuhiko/flask/blob/master/flask/helpers.py

""" END """

##
## Video Object
##
class Video(Base, Serializer):
    __tablename__ = 'video'

    ## Ony public columns get serialized for output through web services!!
    __public__ = [ 'title', 'description',
                   'filename', 'mimetype',
                   'lat', 'lng',
                   'created',
                   'uuid', 'user_id',
                   'size', 'uri' ]

    id = Column(Integer, primary_key=True)

    owner_id    = Column(Integer)
    title       = Column(String(400))
    description = Column(String(4000))
    filename    = Column(String(1024))
    lat         = Column(Numeric(11,8))
    lng         = Column(Numeric(11,8))
    recording_date = Column(DateTime)
    created     = Column(DateTime)
    uuid        = Column(String(40))
    user_id     = Column(String(40))
    mimetype    = Column(String(40))
    size        = Column(Integer)
    uri         = Column(String)
    
    def __init__( self, filename, uuid, user_id, mimetype, size, uri ):
        self.filename = filename
        self.uuid = uuid
        self.user_id = user_id
        self.mimetype = mimetype
        self.size = size
        self.uri = uri

    def __repr__(self):
        return "<Video('%s', '%s')>" % (self.uuid, self.uri)

    def toJSON( self ):
        return json.dumps(self, cls=SWEncoder, indent=2)

videos_table = Video.__table__
metadata = Base.metadata

