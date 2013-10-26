from sys import modules
from sqlalchemy.orm import relationship
from base import BaseModel, Serializer, reflect

"""
You must have a little blurb like the ones below
for every table.  A table may have a __private__
array of columns that should not apprear when the
table is serialized to JSON.  It is optional and
if not present, all columns will appear in the
serialized output.
"""

class Users(BaseModel, Serializer):
    __private__ = ['id', 'password']
    pass

class Media(BaseModel, Serializer):
    __private__ = ['id', 'user_id']
    pass

class MediaAssets(BaseModel, Serializer):
    __private__ = ['id', 'media_id']
    pass

class MediaTypes(BaseModel, Serializer):
    pass

class AssetTypes(BaseModel, Serializer):
    pass

class FeatureTypes(BaseModel, Serializer):
    pass

class Contacts(BaseModel, Serializer):
    pass

class MediaAssetFeatures(BaseModel, Serializer):
    pass

class MediaComments(BaseModel, Serializer):
    pass

class ShareTypes(BaseModel, Serializer):
    pass

class MediaShares(BaseModel, Serializer):
    pass

class Sessions(BaseModel, Serializer):
    pass

class Roles(BaseModel, Serializer):
    pass

class PendingUsers(BaseModel, Serializer):
    pass

class PasswordResets(BaseModel, Serializer):
    pass

class Workorders(BaseModel, Serializer):
    pass

class MediaWorkorders(BaseModel, Serializer):
    pass

class UserRoles(BaseModel, Serializer):
    pass

class Providers(BaseModel, Serializer):
    pass

"""
Well, reflection really only gives us the column definitions it
seems.  We are still responsible for establishing the relationships
between the tables for ORM queries.  The Perl DBIx does this for
you automatically!

"""
def db_map(engine):
    models=modules['vib.db.models']
    mappers, tables, SessionFactory = reflect(engine, models)
    mappers["users"].add_properties({
            "media": relationship(models.Media,
                                  lazy="dynamic",
                                  backref="user",
                                  cascade="all, delete-orphan")
            })
    mappers["media"].add_properties({
            "assets": relationship(models.MediaAssets,
                                   backref="media",
                                   cascade="all, delete-orphan")

            })
    mappers["media_assets"].add_properties({
            "media_asset_features": relationship( models.MediaAssetFeatures,
            backref="media_assets",
            cascade="all, delete-orphan" ) } )
    mappers["contacts"].add_properties( {
            "media_asset_features" : relationship( models.MediaAssetFeatures, backref="contacts" ) } )
    # return (mappers, tables, Session)
    return SessionFactory

