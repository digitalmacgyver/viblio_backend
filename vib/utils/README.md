Viblio Utilities
================

This package holds various scripts and modules that are not easily
placed anywhere else.

Module Index:
-------------

* [Serialize](https://github.com/viblio/video_processor/wiki/Global-serialize-module) - A general purpose locking module that uses our [database](../../schema/README.md) to enforce global locks across our distributed system when all lockers use it
  * Used by FaceRecognition to ensure we only process one video of a user at a time to ensure we recognize similar faces in videos that are concurrently going through our pipeline
  * The example.py and test.py scripts exercise and show examples of the Serialize module
* [s3](s3.py) - A module to upload and download files to S3 given a filename, bucket, and key
  * s3.upload_file( filename, bucket, key )
  * s3.download_file( filename, bucket, key )

Utility Index:
--------------

* [collect-recog-errors.py](collect-recog-errors.py) - A simple script to generate lists of things detected by our face detector but marked by our face recognition pipeline as unusable
* [clone_user.py](clone_user.py) - A script to perform a limited clone of a given user.uuid with a new email
* [create_hittype.py](create_hittype.py) - A script to create an Amazon Mechanical Turk HITType
* [delete_user.py](delete_user.py) - A script to delete users and their files, or optionally just delete all data for a user
* [get_faces.py](get_faces.py) - A script to download all the face images for the last 10 days along with their associated face detection metadata
* [grant_mturk_qualification.py](grant_mturk_qualification.py) - A script to grant the VibWork qualification to an Amazon Mechanical Turk worker so they are able to see our face recognition tasks
* [manage_demo_accounts.py](manage_demo_accounts.py) - A script driven from cron on prod-utils to manage our demo accounts
* [notify_mturk_workers.py](notify_mturk_workers.py) - A script run from cron on our EC2 prod-vwf1 instance once every 2 hours to send the list of MTurk workers in the body of the script notification that there is work pending
* [rescue_orphan_faces.py](rescue_orphan_faces.py) - A script that finds faces detected by our face detection, but not processed by our face recognition pipeline, and creates contacts and adds them to accounts
  * This handles videos that get as far as face detection, and then never finish their workflow for some reason or other

