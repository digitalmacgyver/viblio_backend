Transcode/Transcode
===================

Responsible for transcoding video files, and creating thumbnails and
posters.

Required inputs
---------------

```
{ media_uuid   : ..., 
  user_uuid    : ..., 
  input_file   : { s3_bucket : ..., s3_key : ... },
  metadata_uri : ...,
  original_uuid : ..., # The media_asset uuid of the original video

  # An array of output formats, they will all be transcoded in
  #  parallel for efficiency
  outputs : [ { output_file : { s3_bucket : ..., s3_key : ... },
                format : "mp4", 
                max_video_bitrate: 1500, # Units are kilobits per second
                audio_bitrate : 160,
                size: "640x360", # ***NOTE:*** Presently this is ignored
                asset_type: "main", # ***NOTE:*** There can only be one main asset type, the rest should be video
		# An array of thumbnail images
                thumbnails : [ {
                        times : [0.5], #***NOTE:*** Even though times is an array, only one value is supported
                        size: "320x240", 
                        label: "poster", #***NOTE:*** A poster type is mandatory
                        format : "png",
                        output_file: { s3_bucket, s3_key } } ]
                     },
                        times : [0.5], #***NOTE:*** Even though times is an array, only one value is supported
                        size: "128x129", 
                        label: "thumbnail", #***NOTE:*** A thumbnail type is mandatory
                        format : "png",
                        output_file: { s3_bucket, s3_key } } ]
                     } ] }
```

Outputs
-------

```
{ 
    'media_uuid' : media_uuid,
    'user_uuid' : user_uuid,
    # The 'main' media file's S3 location
    'output_file' : {
                    's3_bucket' : return_bucket,
                    's3_key' : return_key
                    }
                }
```

Side Effects
------------

Creates database rows:

* media_assets table:
  * One row per item in the "outputs" input array with an asset_type corresponding to the asset_type value of input
  * One row per thumbnail item in the "outputs" input array with asset_types corresponding to the label value of the thumbnail

External Dependencies
----------------------

Relies on FFMPEG and related libraries being installed.