video_processor
===============

Code for the server side of the uploader and video processing
pipeline.

This repository has the following modules:

* [app_config](https://github.com/viblio/video_processor/wiki/Uploading-the-tray-app) - Utility for uploading the tray application to our servers
* [brewtus](./brewtus/README.md) - Server side of our file uploader, written in Node.JS
* [cron](./cron/README.md) - Crontab files for our deployments
* [popeye](./popeye/README.md) - Legacy video processing pipeline - currently only uploads files recieved by Brewtus to S3, stores a record of them in the database, and initiates the new pipeline
* [schema](./schema/README.md) - The RDS SQL schema for the site and back end

