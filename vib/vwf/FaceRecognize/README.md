FaceRecognize/Recognize
=======================

Responsible for consolidating the detected faces from FaceDetect and:

* Removing images which are not faces
* Removing images which are part of tracks that contain multiple different faces
* Removing images which are too blurry or unrecognizable
* Merging tracks of images which are of the same person

FaceRecognize relies on SWF timeouts and restarts, and unique task IDs
in Mechanical Turk, and the [Serialize](https://github.com/viblio/video_processor/wiki/Global-serialize-module) module to ensure:

* We process the tracks and faces for each video only once
* A process or server crash does not result in a lost or failed task
* Only one FaceRecognize Activity is active for a given user (this ensures we merge all possible faces, if multiple FaceRecognize Activities were concurrently active for one user we could not merge faces present in those videos with one another)

The flow for this Activity is:

1. Create Mechanical Turk HIT to Merge Tracks
2. Poll Mechanical Turk until the HIT is complete
3. Create N Mechanical Turk HITs for Face Recognition
4. Poll Mechanical Turk until all N HITs are complete
5. Update the database with data about who was recognized

Because the human interaction in steps 1 and 3 could take a long time,
this activity has a long timeout in our SWF workflow.

Because a message may get missed, or a process killed, there is a 5
minute heartbeat timeout on the Recognize job.

In the event that a job has started and times out, we use the same
unique identifiers in Mechanical Turk, and instruct Mechanical Turk to
not re-create the task if it already exists.

Required inputs
---------------

A complex data structure with many fields corresponding to the aspects
of the detected faces, and abbreviated version is:

```
{
  media_uuid : ...,
  user_uuid : ...,
  tracks : [
    { 
      track_id : 0,
      faces : [
        { 
          s3_key : ...,
          s3_bucket : ...,
          ... various face quality metrics ...
        },
        ...
      ]
    },
    ...
  ]
}
```

Outputs
-------

```
{
  media_uuid : ...,
  user_uuid : ...
}
```


Side Effects
------------

Creates database rows:

* contacts table:
  * One new contact for each face which was not recognized as a prior face

Updates database rows:

* media_asset_features table for each face in a given track:
  * Faces that are associated with contacts:
    * Recognized faces get a contact_id of the appropriate contact
    * New faces get a contact_id of the newly created contact
  * Faces that do not get contacts:
    * Non-faces get a recognition_result of ```non_face```
    * Unrecognizable faces get a recognition_result of ```bad_face```
    * Tracks that had 2 or more distinct faces get a recognition_result of ```two_face```

