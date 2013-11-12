Database Connectivity
=====================

This module provides simplified access to our [MySQL
database](../../schema/README.md) via the
[SQLAlchemy](http://www.sqlalchemy.org/) package.

Overview
--------

SQLAlchemy provides two ways to interact with the database:
* Through an Object Relational Mapper (ORM)
* SQL Expressions

Generally our code uses the ORM method, as it simplifies managing the
foreign keys of our system, and that is the only method provided via
this module.

Examples
--------

A good example of how to interact with the database via the ORM can be
found in [vib/vwf/FaceRecognize/db_utils.py](../vwf/FaceRecognize/db_utils.py)

