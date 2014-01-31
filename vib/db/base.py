"""
The base class for all data models.  This basic mechanism allows
for a "reflective" use of the SQL schema; that is, the schema is
the master and out data models are automatically, for the most
part, generated by the schema.

Our base class has some unique features.  It provides for
object constructors that can take a JSON-style dict as an
argument to initialize the attributes, or the more traditional
named keyword style.

It also provides a toJSON() instance method that will return
a JSON string for serialization.

This module also supplies a standalone toJSON() function that
can take a dictionary or a sqlalchemy object, or a hierarchitcal
structure of such things and serialize it:

from base import toJSON
print toJSON({ 'user': orm.query( Users ).first() })

"""
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.orm.session import object_session
import json
import datetime

class Serializer( object ):
    __private__ = []

    def to_serializable_dict( self ):
        dict = {}
        tmp = self.__dict__.copy()
        for key in tmp:
            if key.startswith( '_sa_' ): continue
            if not key in self.__private__:
                value = getattr( self, key )
                if value:
                    dict[key] = value
        return dict

class SWEncoder( json.JSONEncoder ):
    def default( self, obj ):
        if isinstance( obj, Serializer ):
            return obj.to_serializable_dict()
        if isinstance( obj, ( datetime.datetime ) ):
            return obj.isoformat()
        return json.JSONEncoder.default( self, obj )

def toJSON( *args, **kwargs ):
    return json.dumps( dict( *args, **kwargs ), cls=SWEncoder, indent=2 )
    # stolen: https://github.com/mitsuhiko/flask/blob/master/flask/helpers.py

# Three alternative methods exist for constructing new
# objects.
#
# o = Model({ 'col1': 'val', 'col2': 'val' })
#
# o = Model( col1='val', col2='val' )
#
# o = Model()
# o.col1 = 'val'
# o.col2 = 'val'
#
class BaseModel( object ):
    @property
    def session( self ):
        return object_session( self )

    def toJSON( self ):
        return json.dumps( self, cls=SWEncoder, indent=2 )

    def __init__( self, *args, **kwargs ):
        if args and args[0]:
            dic = args[0]
            for k in dic:
                setattr( self, k, dic[k] )
        for key in kwargs:
            setattr( self, key, kwargs[key] )

def reflect( engine, models ):
    metadata = MetaData()
    # metadata.bind = create_engine(engine)
    metadata.bind = engine
    metadata.reflect()
    mappers = {}

    orm_tables = {
        'asset_types' : True,
        'contacts' : True,
        'contact_groups' : True,
        'email_users' : True,
        'faces' : True,
        'feature_types' : True,
        'links' : True,
        'media' : True,
        'media_albums' : True,
        'media_asset_features' : True,
        'media_assets' : True,
        'media_comments' : True,
        'media_shares' : True,
        'media_types' : True,
        'media_workflow_stages' : True,
        'media_workorders' : True,
        'password_resets' : True,
        'pending_users' : True,
        'profiles' : True,
        'profile_fields' : True,
        'providers' : True,
        'recognition_feedback' : True,
        'roles' : True,
        'sessions' : True,
        'share_types' : True,
        'user_roles' : True,
        'users' : True,
        'workflow_stages' : True,
        'workorders' : True
        }

    for table_name in metadata.tables:
        if table_name not in orm_tables: continue
        model_name = "".join( part.capitalize()
                              for part in table_name.split( "_" ) )
        try:
            model = getattr( models, model_name )
        except AttributeError:
            raise NameError, "Model %s not found in module %s" \
                % ( model_name, repr( models ) )
        mappers[table_name] = mapper( model, metadata.tables[table_name] )

    # I took this Session out in favor of the scoped_session() being
    # done in load_sqla() in popeye.py, when new requests come in.
    SessionFactory = sessionmaker( metadata.bind, autocommit=False, autoflush=True )
    # Session = None
    return ( mappers, metadata.tables, SessionFactory )
