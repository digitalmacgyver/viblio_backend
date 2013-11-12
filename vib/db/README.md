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

***NOTE:*** We use MySQL InnoDB as our database back end.  InnoDB uses [consistent reads](http://dev.mysql.com/doc/refman/5.0/en/innodb-consistent-read.html).  This coupled with the SQLAlchemy session behavior of always being in a transaction has this important consequence:

**Your queries against the database will reflect the contents of the database as of the completion of your prior transaction, or the call to vib.db.orm.get_session().  This means, for example, if you are waiting for a new row to appear and simply loop while querying the database, your row will never show up.**

To view the contents of the database "as of now" issue a commit()
(which preserves all changes made in your session so far) or a
rollback() (which abandons them) before performing a query.

Examples
--------

An example of how to interact with the database via the ORM can be
found in
[vib/vwf/FaceRecognize/db_utils.py](../vwf/FaceRecognize/db_utils.py)

An example of how to interact with the database without the ORM (and
without this module) can be found in
[vib/utils/Serialize.py](../utils/Serialize.py)

Usage
-----

Simple usage is:
```
import vib.db.orm
from vib.db.models import *

orm = vib.db.orm.get_session()

# Get some rows
results = orm.query( TableOfInterest ).filter( TableOfInterest.columnName1 == 3 )

# See their contents
for result in results:
    print result.columnName1, result.columnName2, ...

# Change their contents
result.columName1 = 0

# Create a new row
new_row = TableOfInterest( 
	columnName1 = value1,
	columnName2 = value2,
	... )

# Safe the result of both the change and the creation.
orm.commit()
```

Package Contents
----------------

### Interface Modules

* [orm.py] - Provides the get_session method which returns an session that ORM operations can be performed upon.
  * Get session also validates that the session returned has a valid DB connection before returning it
* [models.py](./models.py) - Provides class names for the ORM tables of interest, e.g. Media, MediaAssets, Users, Contacts
  * Also describes how tables relate to one another via the db_map engine

### Internal Modules
* [base.py](./base.py) - underlying glue, the only user serviceable part is the orm_tables data structure in the reflect function that shows what tables are available from the ORM
