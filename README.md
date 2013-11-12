video_processor
===============

Code for the server side of the uploader and video processing
pipeline.

This repository has the following modules:

Main Modules
------------
* [brewtus](./brewtus/README.md) - Server side of our file uploader, written in Node.JS
* [popeye](./popeye/README.md) - Legacy video processing pipeline - currently only uploads files received by Brewtus to S3, stores a record of them in the database, and initiates the new pipeline
* [schema](./schema/README.md) - The RDS SQL schema for the site and back end
* [vib](./vib/README.md) - The root of the new backend Python application tree

Minor Modules
-------------

* [app_config](https://github.com/viblio/video_processor/wiki/Uploading-the-tray-app) - Utility for uploading the tray application to our servers
* [cron](./cron/README.md) - Crontab files for our deployments
* [test](https://github.com/viblio/video_processor/wiki/Create-Test-Data) - Utilities used to create some basic test data for testing accounts
* tuspy - A utility for uploading movie files into our pipeline, run tuspy.py --help for details
* utils - A deprecated serialization utility originally used by popeye, do not use

