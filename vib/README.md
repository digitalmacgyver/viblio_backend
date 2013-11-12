vib
===============

The root of our back end video processing Python repository.  Includes
multiple utilities, applications, and configuration elements.

Running Code in the Repository
------------------------------

Code in the repository typically requires that PYTHONPATH include the
parent of the vib directory, and certain elements require the
BOTO_CONFIG environment variable to be set.

To establish these environment variables:
```
cd video_processor/vib
source setup-env.sh
```

Main Modules
------------

* [config](./config/README.md) - Holds the configuration module, and configuration files, used by the various utilities and programs in vib
* [db](./db/README.md) - The [SQLAlchemy](http://www.sqlalchemy.org/) based database interaction module for interacting with [our database](../schema/README.md)
* [vwf](./vwf/README.md) - The Video Workflow pipeline that processes our videos once [Popeye](../popeye/README.md) initiates the workflow
..* There are several subcomponents of vwf


Minor Modules
-------------

* [fb](./fb/README.md) - Module for Facebook interaction, presently only used to import Facebook contacts and tagged photos of a user and their friends
* [rekog](./rekog/README.md) - Module for interaction with [ReKognition](http://www.rekognition.com/), a web service that performs face recognition
* [thirdParty](./thirdParty/README.md) - Module for installing third party code and tools
* [utils](./utils/README.md) - Module for utility scripts and code used by multiple applications (e.g. S3 interaction code, our Serialization module)