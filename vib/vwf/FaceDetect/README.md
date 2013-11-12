FaceDetect/Detect
===================

Responsible for detecting faces in video files.  Detects faces and
then creates "tracks" which are a series of images of (presumably) the
same face.

Required inputs
---------------

```
{ media_uuid   : ..., 
  user_uuid    : ..., 
  Transcode : {
     output_file : {
        s3_key : ...,
        s3_bucket : ..,
     }
  }
}
```

Outputs
-------

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

Side Effects
------------

Creates database rows:

* media_assets table:
  * One row per "face" item of asset_type "face"
* media_asset_features table:
  * One row per "face" item of asset_type "face" with a "coordinates" field of the value of the faces data structure

External Dependencies
----------------------

Relies on FFMPEG and related libraries being installed, and the
/deploy/vatools package.