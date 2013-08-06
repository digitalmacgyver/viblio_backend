"""
Our data models.  For each table in the database, there is a corresponding
model specified here in this file.  These models are used by the application code in
database operations.  See http://docs.sqlalchemy.org/en/rel_0_8/orm/tutorial.html.

"""
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey

from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import datetime
import json

# Application config
from appconfig import AppConfig
config = AppConfig( 'popeye' ).config()

# Create the database engine
engine = create_engine( 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name )

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

## User 
##
class User( Base, Serializer ):
    __tablename__ = 'users'
    __public__ = [ 'uuid', 'provider', 'provider_id',
                   'username', 'email',
                   'displayname' ]

    id = Column(Integer, primary_key=True)
    media = relationship( 'Media' )

    uuid = Column(String(36))
    provider = Column(String(16))
    provider_id = Column(String(45))
    username = Column(String(128))
    password = Column(String(128))
    email = Column(String(256))
    displayname = Column(String(128))
    active = Column(String(32))
    accepted_terms = Column(Boolean)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)

    def __repr__(self):
        return "<User('%s', '%s')>" % (self.uuid, self.username)

    def toJSON( self ):
        return json.dumps(self, cls=SWEncoder, indent=2)

class MediaType( Base ):
    __tablename__ = 'media_types'
    type_t = Column('type',String(16), primary_key=True)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)

class AssetType( Base ):
    __tablename__ = 'asset_types'
    type_t = Column('type',String(16), primary_key=True)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)

##
## Media Object
##
class Media(Base, Serializer):
    __tablename__ = 'media'

    ## Ony public columns get serialized for output through web services!!
    __public__ = [ 'title', 'description',
                   'filename', 'media_type',
                   'lat', 'lng',
                   'created_date',
                   'uuid' ]

    id = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('users.id'))
    assets = relationship( 'MediaAsset' )

    uuid        = Column(String(36))
    media_type = Column(String(16), ForeignKey('media_types.type'))
    title       = Column(String(200))
    filename    = Column(String(1024))
    description = Column(String(1024))
    recording_date = Column(DateTime)
    view_count = Column(Integer)
    lat         = Column(Numeric(11,8))
    lng         = Column(Numeric(11,8))
    created_date = Column(DateTime)
    updated_date = Column(DateTime)

    """
    def __init__( self, filename, uuid, user_id, mimetype, size, uri ):
        self.filename = filename
        self.uuid = uuid
        self.user_id = user_id
        self.mimetype = mimetype
        self.size = size
        self.uri = uri
    """

    def __repr__(self):
        return "<Media('%s', '%s')>" % (self.uuid, self.filename)

    def toJSON( self ):
        return json.dumps(self, cls=SWEncoder, indent=2)

##
## Media Asset Object
##
class MediaAsset(Base, Serializer):
    __tablename__ = 'media_assets'

    ## Ony public columns get serialized for output through web services!!
    __public__ = [ 'uuid', 'asset_type',
                   'filename', 'mimetype',
                   'uuid', 'location',
                   'size', 'uri' ]

    id = Column(Integer, primary_key=True)
    media_id    = Column(Integer, ForeignKey('media.id'))

    uuid        = Column(String(36))
    asset_type  = Column(String(16), ForeignKey('asset_types.type'))
    mimetype    = Column(String(40))
    filename    = Column(String(1024))
    uri         = Column(String)
    location    = Column(String(28))
    format      = Column(String(40))
    duration    = Column(Numeric(14,16))
    bytes       = Column(Integer)
    width       = Column(Integer)
    height      = Column(Integer)
    time_stamp   = Column(Numeric(14,16))
    metadata_uri = Column(String)
    provider = Column(String(16))
    provider_id = Column(String(45))
    view_count = Column(Integer)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    
    def __repr__(self):
        return "<MediaAsset('%s', '%s')>" % (self.uuid, self.uri)

    def toJSON( self ):
        return json.dumps(self, cls=SWEncoder, indent=2)

users_table = User.__table__
media_types_table = MediaType.__table__
media_table = Media.__table__
asset_types_table = AssetType.__table__
media_assets_table = MediaAsset.__table__

metadata = Base.metadata

