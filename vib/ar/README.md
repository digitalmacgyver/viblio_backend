# Activity Recognition System

The Viblio Activity Recognition System is a Software as a Service
generalized activity recognition system for video and images.  It is
accessed through a web services API, and indirectly through the Viblio
consumer app.

The system is made up of these major components:

* An API that allows users to add and tag videos and images with activities, train models, evaluate the accuracy of their models, and classify videos and images.
* The Viblio core activity library of recognizable activities that any user can access through the API
* An demo website showing how the AR system performs for a given input video or image
* An admin website allowing Viblio employees to manage the Viblio core activity library 

Additionally, the system will be integrated with the Viblio consumer app to provide:

* Activity based search, ranking, and magic tagging of videos for users of the app
* Improvements to the Viblio library of core activities based on user feedback in the Viblio consumer app

This document contains:

1. Activity Recognition API Reference
2. [TBD - Internal Workflow Specification](#workflow)
3. [TBD - Internal Data Architecture](#data)

## Activity Recognition API Reference

### API Overview and Implementation Priorities

The entire Activity Recognition (AR) system will be a large and
complex undertaking.  We prioritize the portions of the API which
allow us to:

1. Capture useful data we are currently throwing away, so as to build a CV library to make future work faster.
2. Reduce or eliminate manual steps

<a name="api_summary"></a>

Category | API Name | Priority | Notes
---------|----------|----------|------
**CV Library** | | |
 | [create_videos](#create_videos) | V1 | Storing videos in the AR system allows us to build a library of reusable CV resources.
 | [create_images](#create_images) | V1 | Storing images in the AR system allows us to build a library of reusable CV resources.
 | [update_videos](#update_videos) | V1 | Storing known tags in the AR system is the most valuable piece of a reusable CV library.
 | [update_images](#update_images) | V1 | Storing known tags in the AR system is the most valuable piece of a reusable CV library.
 | [list_media](#list_media) | V1 | CV library unusable without retrieval mechanism.
**Enable Training and Testing Forensics** | | |
 | [create_model](#create_model) | V2 | The main purpose of forcing this into the API now is to allow us to track what images went into a model easily
 | [update_model](#update_model) | V2 | The main purpose of forcing this into the API now is to allow us to track what images went into a model easily
 | [list_models](#list_models) | V2 | Easy and simplifies usage of models
**SaaS Offering** | | | 
 | [classify_video](#classify_video) | V3 | Allows Viblio video processing workflow to integrate with AR system - prerequisite to having > 5 or so activities live in Viblio.  Also prerequisite before we could sell this API as a service.  However, time consuming and involves a lot of unknowns today - so not slated for the current version.
 | [classify_image](#classify_image) | V3 | Trivial once classify video is done
 | [delete_media](#delete_media) | V3 | Eventually we'll want to be able to delete stuff
 | [delete_model](#delete_model) | V3 | Eventually we'll want to be able to delete stuff
 | [extract_images](#extract_images) | Future | We already have a utility that slices out images from a video.
 | [download_media](#download_media) | Future | This would be required before we could re-sell this system.
**Automation** | | |
 | [test_model](#test_model) | Future | Full of unknowns today (what features will we support, how will we aggregate frames etc.), once we settle down on those areas we can bring this into the API

### Tags and Classifications

Each media item in the AR system (video or image) can have multiple
tags and classifications associated with it.  

Tags are provided by users of the AR system, classifications are
provided by the AR system itself.

A tag embodies activity information about the media which is external
to our AR system, it is presented in a data structure like this:

```
{ name : "string", # Required, the name of the activity
  tag_source : "Whence", # Optional, the source of the tag, for example MTurk or Imagenet
  present : [ { interval : [s0, e0] }, { interval : [s1, e1] }, ... ] # Required for videos, not allowed for images, the timecodes in the video when the activity is present
}
```

A classification is a statement of confidence about what the video
contains according to the AR system, it is presented in a data
structure like this:

```
{ name : "string" # Required, the name of the activity
  classification_source : "viblio" or "user" # Required, who has provided this classification
  classification_model : model_uid # The model which provided this classification
  present : [ { confidence : 0.75, interval : [s0, e0] }, { confidence : 0.02, interval : [s1, e1] }, ... ] # Required for videos, not allowed for images, the timecodes in the video when the activity is present along with the AR system confidence of that, ranging from 0-1.
}
```

### Common Parameters

All APIs support the following parameters, unless stated otherwise:

Required | Name | Description
---------|------|------------
Required | api_key | Your ViblioAR API Key
Required | api_secret | Your ViblioAR API Secret
Required | job | The specific API action to take for this call
Optional | app | The app you are making calls on behalf of, defaults to: default
Optional | user | The user you are making calls on behalf of, defaults to: default

The ( app, user ) tuple defines the scope of an operation.  For
example, an image added and trained for ( App1, User2 ) will not
impact recognition results for ( AppX, UserY ) when X is not 1 or Y is
not 2.

### Behavior on Failures

Many of the jobs below operate on arrays of input videos or images, or
produce multiple outputs.  In the event of an error, all these
operations are treated as a single transaction with regard to the AR
system.  If any portion of a job has an error, then all changes for
the entire job will be backed out of the AR system.

### <a name="create_videos"></a>create_videos job

[Back to API summary](#api_summary)

Add videos to the AR system, this method runs asynchronously.  It will
return errors of API usage synchronously, but returns the general
success messages through a callback_url or via email.

##### Inputs

Required | Name | Description
---------|------|------------
Required | job | create_videos
Required | videos | An array of video data structures, defined below
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to

The input video data structure is:

```
{ source : # Either "s3" or "url",
  # If source is url
  url : # direct download URL to video,
  # If source is s3
  s3_file : {
    s3_key : # Required
    s3_bucket : # Required
    aws_access_key : # Optional, provide if the s3 file is not publicly available
    aws_secret_key : # Optional, provide if the s3 file is not publicly available
  },
  video_external_uid : "string" # Optional, if provided this field will be associated with this video
  set_name : "string" # Optional, if provided this field will be associated with this video
  public : true, # Optional, if true then a public URL to this resource will be created, defaults to true
  tags : [ # Optional
     { name : tag1_name,
       tag_source : , # A string that can be used to identify the source of the tag, such as Imagenet DB or MTurk
       present : [ { interval : [s0, e0] }, { interval : [s1, e1] }, ... ], # Array of start, end times in the video when tag1_name is present
     },
     { name : tag2_name ,
       ...
     },
     ...
  ]
}
```

##### Output is an wrapped array of file upload data structures with one element per videos array element

Note, if no callback_url or result_email is provided, not output is
provided.  The user can poll for when this video is available within
the AR system by specifying an video_external_uid an using the list_media
job.  If an error occurs, the video may never be made available.

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "create_videos",
  results : [ { 
    video_uid : # Globally unique string identifier of this video in the AR system
    video_external_uid : # If one was provided on input, it will be returned
    set_name : # If one was provided on input, it will be returned
    url : # If public was not false, a URL to this video in the AR system is provided
    },
    { ... },
  ]
}
```

Notes: 
* If video_external_uid is provided, it must be unique per video within the ( app, user ) space
* set_name is intended to identify groups of related media (video clips and images) that come from the same original source, which in turn allows the user to ensure they do not train and test on images from the same ultimate source

### <a name="create_images"></a>create_images job

[Back to API summary](#api_summary)

Add images to the AR system, this method runs asynchronously.  It will
return errors of API usage synchronously, but returns the general
success messages through a callback_url or via email.

##### Inputs

Required | Name | Description
---------|------|------------
Required | job | create_images
Required | base64 or images | either a base64 encoded image, or an array of image data structures, defined below
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to

If the images argument is provided, it contains an array of this image input data structure:

```
{ source : # Either "s3" or "url",
  # If source is url
  url : # direct download URL to image,
  # If source is s3
  s3_file : {
    s3_key : # Required
    s3_bucket : # Required
    aws_access_key : # Optional, provide if the s3 file is not publicly available
    aws_secret_key : # Optional, provide if the s3 file is not publicly available
  },
  image_external_uid : "string" # Optional, if provided this field will be associated with this image
  set_name : "string" # Optional, if provided this field will be associated with this image
  source_video_uid : # Optional, if provided indicates this image came from the AR system video with this video_uid
  source_video_external_uid : # Optional, if provided, indicates this image came from the AR system video with this video_external_uid
  source_video_timecode : # Optional, if provided, indicates this image came from this timecode in floating point seconds from the source video
  public : true, # Optional, if true then a public URL to this resource will be created, defaults to true
  tags : [ # Optional
     { name : tag1_name,
       tag_source : , # A string that can be used to identify the source of the tag, such as Imagenet DB or MTurk
     },
     { name : tag2_name ,
       ...
     },
     ...
  ]
}
```

If the base64 argument is provided, its input is this data structure:

```
{ source : "base64",
  data : "base64 encoded string of the image",
  image_external_uid : "string" # Optional, if provided this field will be associated with this image
  set_name : "string" # Optional, if provided this field will be associated with this image
  source_video_uid : # Optional, if provided indicates this image came from the AR system video with this video_uid
  source_video_external_uid : # Optional, if provided, indicates this image came from the AR system video with this video_external_uid
  source_video_timecode : # Optional, if provided, indicates this image came from this timecode in floating point seconds from the source video
  public : true, # Optional, if true then a public URL to this resource will be created, defaults to true
  tags : [ # Optional
     { name : tag1_name,
       tag_source : , # A string that can be used to identify the source of the tag, such as Imagenet DB or MTurk
     },
     { name : tag2_name ,
       ...
     },
     ...
  ]
}
```

##### Output is an array of file upload data structures with one element per images array element

Note, if no callback_url or result_email is provided, not output is
provided.  The user can poll for when this image is available within
the AR system by specifying an image_external_uid an using the list_media
job.  If an error occurs, the image may never be made available.

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "create_images",
  results : [ { 
    image_uid : # Globally unique string identifier of this image in the AR system
    image_external_uid : # If one was provided on input, it will be returned
    set_name : # If one was provided on input, it will be returned
    url : # If public was not false, a URL to this image in the AR system is provided
    },
    { ... },
  ]
}
```

Notes: 
* It is an error if any source image can not be uploaded.
* Either images or base64 must be provided, it is an error to provide both.
* If image_external_uid is provided, it must be unique per image within the ( app, user ) space.
* set_name is intended to identify groups of related media (video clips and images) that come from the same original source, which in turn allows the user to ensure they do not train and test on images from the same ultimate source

### <a name="extract_images"></a>extract_images job

[Back to API summary](#api_summary)

Takes an input video already in the AR system, and extracts images at
some frequency throughout the video.  This method returns its data
asynchronously through a callback_url or email (excepting the case of
API usage errors, which are returned synchronously).

##### Inputs

Required | Name | Description
---------|------|------------
Required | job | extract_images
Required | extract_videos | An array of existing videos in the AR system
Optional | frequency | Floating point number, an image will be extracted every 1/frequency seconds.  Defaults to 1.
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to

The elements of the extract_videos data structure are:

```
{ # One of either video_uid, or video_external_uid is required
  video_uid : 123,
  video_external_uid : 'whatever was input for this video',
  propagate_set_name : true # Optional, if provided the resulting images will have their set_name set to that of the source video, defaults to true
  public : true # Optional, if provided the resulting images will be available by public URL in the AR system, defaults to true
} 
```

As a result of this operation many new images will be stored in the AR
system, optional fields will be populated in this manner:

Field | Value
------|------
set_name | If propagate_set_name is set in the extract_videos data structure the value from the source video, otherwise null
source_video_uid | The video_uid of the source video
source_video_external_uid | The video_external_uid of the source video (which could be null)

##### Output is a nested array of [video][image] data structures with one element per video per image extracted

Note, if no callback_url or result_email is provided, not output is
provided.  The user can poll for when these images are available
within the AR system by searching for images with the appropriate
source_video_uid or _external_uid using the list_media job.  If an
error occurs, the images may never be made available.

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "extract_images",
  results : [ { 
    video_uid : # The source video
    video_external_uid : # The external UID of the source video
    set_name : # The set_name of the source video
    extracted_images : [
        { 
          image_uid : # Globally unique string identifier of this image in the AR system
	  source_video_timecode : # The timecode in floating point seconds from the video where this image was extracted
	  source_video_uid : ...,
	  source_video_external_uid : ...,
          set_name : ...,
          url : # If public was not false, a URL to this image in the AR system is provided
        },	
        { ... },
      ]
    },
    { video_uid : ... },
  ]
}
```

### <a name="update_videos"></a>update_videos job

[Back to API summary](#api_summary)

This job returns its results synchronously.

##### Inputs

Required | Name | Description
---------|------|------------
Required | job | update_videos
Required | video_tags | An array of video_tag data structures defined below

The video_tag data structure is:

```
{ # Select the video via one of either video_uid, or video_external_uid
  video_uid : 123,
  video_external_uid : 'whatever was input for this video',
  
  # Update fields with these optional arguments:
  new_video_external_uid : 'new desired video_external_uid',
  set_name : 'new set name',
  public : true,
  # To update tags, apply these optional parameters
  # method is "extend" or "replace" - defaults to "extend"
  method : "extend", # Add the tags below to any existing tags for the video
  method : "replace", # Any existing tags for this video are removed, and the tags below are used.
  tags : [
     { name : tag1_name,
       tag_source : , # A string that can be used to identify the source of the tag, such as Imagenet DB or MTurk
       present : [ { interval : [s0, e0] }, { interval : [s1, e1] }, ... ], # Array of start, end times in the video when tag1_name is present
     },
     { name : tag2_name ,
       ...
     },
     ...
  ]
} 
```

##### Output is an wrapped array of these structures with one element per video_tags array element

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "update_videos",
  results : [ { 
    video_uid : # Globally unique string identifier of this video in the AR system
    video_external_uid : # If this video has a uid, it will be returned
    set_name : # If this video has a set_name, it will be returned
    url : # If public was not false for this video, a URL to this video in the AR system is provided
    tags : [ 
        # The tags associated with the video now (which will either be the same as the input if the "replace" method was used, or the entire tag if the "extend" method was used)
      ],   
    },
    { ... },
  ]
}
```

Notes: 
* If both video_uid and video_external_uid are provided on input, the video_uid is used.
* If method : "replace" is used, and no tags are provided, then the video will be set to have no tags

### <a name="update_images"></a>update_images job

[Back to API summary](#api_summary)

This job returns its results synchronously.

##### Inputs

Required | Name | Description
---------|------|------------
Required | job | update_images
Required | image_tags | An array of image_tag data structures defined below

The image_tag data structure is:

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "update_images",

  # Select the image via one of either image_uid, or image_external_uid
  image_uid : 123,
  image_external_uid : 'whatever was input for this image',
  
  # Update fields with these optional arguments:
  new_image_external_uid : 'new desired image_external_uid',
  set_name : 'new set name',
  source_video_uid : 'new desired source_video_uid',
  source_video_external_uid : 'new desired source_video_external_uid',
  public : true,
  # To update tags, apply these optional parameters
  # method is "extend" or "replace" - defaults to "extend"
  method : "extend", # Add the tags below to any existing tags for the video
  method : "replace", # Any existing tags for this video are removed, and the tags below are used.
  tags : [
     { name : tag1_name,
       tag_source : , # A string that can be used to identify the source of the tag, such as Imagenet DB or MTurk
     },
     { name : tag2_name ,
       ...
     },
     ...
  ]
} 
```

##### Output is an array of these structures with one element per image_tags array element

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "update_images",
  results : [ { 
    image_uid : # Globally unique string identifier of this image in the AR system
    image_external_uid : # If this image has an image_external_uid, it will be returned
    set_name : # If this image has a set_name it will be returned
    url : # If public was not false for this video, a URL to this image in the AR system is provided
    tags : [ 
      # The tags associated with the image now (which will either be the same as the input if the "replace" method was used, or the entire tag if the "extend" method was used)
    ]   
  },
  { ... },
]
```

Notes: 
* If both image_uid and image_external_uid are provided on input, the image_uid is used.
* If method : "replace" is used, and no tags are provided, then the image will be set to have no tags

### <a name="list_media"></a>list_media job

[Back to API summary](#api_summary)

This job returns information about images and videos that meet search
criteria.  The results are returned synchronously.

##### Inputs

Required | Name | Description
---------|------|------------
Optional | media_search | A media_search data structure as described below

The search data structure is a dictionary with many optional search
fields.  The fields are divided into three categories: general fields,
tag fields, and classification fields.

For the general fields, providing the fields by passing a value of
null as the argument matches precisely those element which have no
value for that field.  Omitting a field entirely ignores that field
when finding search matches.

Only images present in the union of the results from the general
search, the tag search, and the classification search will be
returned.

Passing an empty dictionary will return all media.

**General Fields**

Required | Name | Description
---------|------|------------
Optional | videos_only | 
Optional | images_only |
Optional | video_uid |
Optional | video_external_uid | 
Optional | image_uid | 
Optional | image_external_uid | 
Optional | set_name | Can find both images and videos
Optional | source_video_uid | 
Optional | source_video_external_uid |

General search fields are additive equality requirements.  So,
searching for set_name="X" and image_external_uid="Y" will yield only
images whose external uid is Y and who have a set name of X.

**Tag Fields**

Required | Name | Description
---------|------|------------
Optional | exclude_tag_sources | An array of strings, if this array is provided images containing tags from these tag_sources are excluded.
Optional | include_tag_sources | An array of strings, if this array is provided only images containing tags from these tag_sources are included in the results.
Optional | One of no_tags, has_tags, exclude_tags, any_tags, or all_tags |
 | no_tags | Media with no tags at all
 | has_tags | Media with one or more tags
 | exclude_tags | Takes a dictionary as an argument, finds media with at least one tag and none of the tags in the argument
 | any_tags | Takes a dictionary as an argument, finds media with any of the tags in the argument
 | all_tags | Takes a dictionary as an argument, finds media with all of the tags in the argument

**Classification Fields**

Required | Name | Description
---------|------|------------
Optional | exclude_classification_sources | An array of strings, if this array is provided images containing classifications from these sources are excluded.  The only valid classification sources are "viblio" and "user".
Optional | include_classification_sources | An array of strings, if this array is provided only images containing classifications from these sources are included in the results.  The only valid classification sources are "viblio" and "user".
Optional | exclude_classification_models | An array of strings, finds images not classified by those models.
Optional | include_classification_models | An array of strings, finds only images classified by those models.
Optional | One of no_classifications, has_classifications, exclude_classifications, any_classifications, or all_classifications |
 | no_classifications | Media with no classifications at all
 | has_classifications | Media with one or more classifications
 | exclude_classifications | Takes a dictionary as an argument, finds media with at least one classification and none of the classifications in the argument
 | any_classifications | Takes a dictionary as an argument, finds media with any of the classifications in the argument
 | all_classifications | Takes a dictionary as an argument, finds media with all of the classifications in the argument
Optional | confidence_lower_bound | Exclude any results whose classification confidence is lower than this
Optional | confidence_upper_bound | Exclude any results whose classification confidence is greater than this

##### Output

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "list_media",
  video_results : [ { 
    video_uid : # Globally unique string identifier of this video in the AR system
    video_external_uid : # If this video has a uid, it will be returned
    set_name : # If this video has a set_name, it will be returned
    url : # If public was not false for this video, a URL to this video in the AR system is provided
    tags : [ 
        # The tags associated with the video
      ],   
    },
    { ... },
  ],
  image_results : [ { 
    image_uid : # Globally unique string identifier of this image in the AR system
    image_external_uid : # If this image has a uid, it will be returned
    set_name : # If this video has a set_name, it will be returned
    source_video_uid : ...,
    source_video_external_uid : ...,
    source_video_timecode : ...,
    url : # If public was not false for this image, a URL to this image in the AR system is provided
    tags : [ 
        # The tags associated with the image
      ],   
    },
    { ... },
  ]
}
```

### <a name="download_media"></a>download_media job

[Back to API summary](#api_summary)

Synchronously initiates a download of a requested media resource.  Note
that if this media is "public" then the URL to that media can be
readily obtained from the list_media API.  This API is primarily
intended for use with "private" media.

##### Inputs

Required | Name | Description
---------|------|------------
Required | One of video_uid, video_external_uid, image_uid, or image_external_uid | 

##### Output

Appropriate mime typed streaming data for the video in question, or a
application/JSON error if no such media is found.

### <a name="create_model"></a>create_model job

[Back to API summary](#api_summary)

Asynchronously creates a model.

Presently we build our model based solely on images, in the future we
may extend this method to take in videos or video clips as part of its
input.

Presently the features we extract for images in training can not be
controlled through the API.  Someday when we have many features we
will give them user friendly names like "image characteristic poses"
or "video motion" and allow users to turn them on and off for a
particular model.

##### Inputs

Required | Name | Description
---------|------|------------
Required | One or both of: positive_images or positive_search |
 | positive_images | An array of image_uid or image_external_uids to use as positives for the model
 | positive_search | An image only search as described in the list_media documentation
Required | One or both of: negative_images or negative_search |
 | negative_images | An array of image_uid or image_external_uids to use as negatives for the model
 | negative_search | An image only search as described in the list_media documentation
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to
Required | model_tag_name | The tag this model will apply to media it classifies.  
Optional | model_version | Integer, defaults to 1

Notes: 

* It is an error to have the same image present in both the positive and negative values for the model
* Behind the scenes, features are created and persisted as a result of this operation for any positive or negative images which do not already have features
* Having images selected twice in both the explicit list and search criteria does not change the model versus ensuring they are only present once
* Model tags that begin with viblio_ are reserved for the Viblio core activity library, it is an error to specify a model_tag_name beginning with viblio_
* The output results will only have one element

##### Output

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "create_model",
  url : # URL to the model, this will eventually be removed from the API once the classify_video and test_model APIs are implemented
  results : [ { 
    model_uid : # Globally unique string identifier of this model in the AR system
    model_tag_name : ...,
    model_version : ...,
    positive_images : [ { image_uid : ..., image_external_uid : ... }, ... ],
    negative_images : [ { image_uid : ..., image_external_uid : ... }, ... ],
  } ]
}
```

### <a name="update_model"></a>update_model job

[Back to API summary](#api_summary)

Asynchronously updates a model.

##### Inputs

Required | Name | Description
---------|------|------------
Required | source_model_uid | The model to be updated
Required | One or both of: positive_images or positive_search |
 | positive_images | An array of image_uid or image_external_uids to use as positives for the model
 | positive_search | An image only search as described in the list_media documentation
Required | One or both of: negative_images or negative_search |
 | negative_images | An array of image_uid or image_external_uids to use as negatives for the model
 | negative_search | An image only search as described in the list_media documentation
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to
Optional | model_tag_name | String, defaults source_model_uid's name
Optional | model_version | Integer, defaults to source_model_uid's version + 1

This table describes what action is taken if an image present in the
positive or negative set was part of a prior training of the source_model

Current Model Set | New Model Set | Action
------------------|---------------|-------
negative | negative | Nothing
negative | positive | Prior negative point untrained, new positive point trained
positive | negative | Prior positive point untrained, new negative point trained
positive | positive | Nothing

Notes: 
* An image that was positive or negative in the source_model can be included in the updated model with the opposite value, but it is still an error to provide the same image in the positive_images/positive_search and negative_images/negative_search sets for the update
* The output results will only have one element

##### Output
```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "update_model",
  url : # URL to the model, this will eventually be removed from the API once the classify_video and test_model APIs are implemented
  results : [ { 
    source_model_uid : # Globally unique string identifier of the source model in the AR system
    model_uid : # Globally unique string identifier of this model in the AR system
    model_tag_name : ...,
    model_version : ...,
    positive_images : [ { image_uid : ..., image_external_uid : ... }, ... ],
    negative_images : [ { image_uid : ..., image_external_uid : ... }, ... ],
  } ]
}
```

### <a name="list_models"></a>list_models job

[Back to API summary](#api_summary)


Synchronously lists the details of a model.

##### Inputs

Required | Name | Description
---------|------|------------
Optional | model_uids | An array of model_uids of interest
Optional | model_tag_names | An array of model_tag_names of interest

If neither model_uids or model_tag_names is provided, all models for the
current app/user will be returned.  If either is provided then all
models matching either criteria will be returned.

##### Output

```
{ app : # The app this job was for
  user : # The user who this job was for
  job : "list_models",
  url : # URL to the model, this will eventually be removed from the API once the classify_video and test_model APIs are implemented
  results : [ { 
      model_uid : # Globally unique string identifier of this model in the AR system
      model_source : "viblio" or "user"
      model_tag_name : ...,
      model_version : ...,
      # For user models only:
      positive_images : [ 
        { image_uid : ..., 
          image_external_uid : ..., 
	  set_name : ...,
	  source_video_uid : ...,
	  source_video_external_uid : ...,
	  source_video_timecode : ...,
	  url : # If public was not false for this image, a URL to this image in the AR system is provided
   	  tags : [ 
            # The tags associated with the image
      	  ], 
        },
        { ... },
      ],
      negative_images : [ ... ],
    },
    { model_uid : ..., ... } 
  ]
}
```

### <a name="classify_video"></a>classify_video job

[Back to API summary](#api_summary)


The classify_video job runs asynchronously.

##### TBD

1. The classify_video job would have a system of recording how it
classified the video, and later recording user feedback on how the
classification was evaluated by the human operator.  This portion of
the interaction is still to be designed.

2. Each AR model will be applied to a video with some particular
strategy of aggregating data across frames.  The set of strategies
available, and what parameters they support are under current
development.

##### Inputs

Required | Name | Description
---------|------|------------
Required | video_uid or video_external_uid | The video to be classified
Optional | viblio_core_activities | Whether to recognize the Viblio Core activities, defaults to true
Optional | model_strategies | An array of model_strategy data structures described below
Optional | callback_url | A url to post the output results to
Optional | result_email | An email address to mail the output results to

For each model we wish to apply to the input video, there are
additional parameters that control how that model evaluates the video.
The details here are TBD, but for example they could include an
"aggregation_strategy" and a "confidence_threshold".

Example model_strategy:

```
{ model_uid : # The model in question
  aggregation_strategy : "sliding_window"
  confidence_threshold : 0.35 }
```

##### Output - A list of classifications which have been applied to the video

```
{ name : "string" # Required, the name of the activity
  classification_source : "viblio" or "user" # Required, who has provided this classification
  classification_model : model_uid # The model which provided this classification
  present : [ { confidence : 0.75, interval : [s0, e0] }, { confidence : 0.02, interval : [s1, e1] }, ... ] # Required for videos, not allowed for images, the timecodes in the video when the activity is present along with the AR system confidence of that, ranging from 0-1.
}
```

### <a name="classify_image"></a>classify_image job

[Back to API summary](#api_summary)


Much the same as classify_video, but without the intervals in the
present array and just a single confidence value.


### <a name="test_model"></a>test_model job

[Back to API summary](#api_summary)


This API will be responsible for combining a model and one or more
aggregation strategies, and producing:

* Optimal threshold and aggregation strategy information for the model over the test set
* Reports on the quality and effectiveness of the model on the test set

When complete it will be a large labor saving device, but presently we
are rapidly changing the methodology for how we take a model and test
it, once that is routine we can formalize it into an API.

### <a name="delete_media"></a>delete_media job

[Back to API summary](#api_summary)


This API will be responsible for deleting images and videos.  Still to
be designed are the rules for what media can be deleted when it has
dependent entities, for example can videos be deleted before their
images, and can videos or images be deleted when there are models
which depend on them (doing so may interfere with the ability to run
the update_model API).

### <a name="delete_models"></a>delete_models job

[Back to API summary](#api_summary)


This API will be responsible for deleting models.

# <a name="workflow"></a>Internal Workflow Specification

TBD 

# <a name="data"></a>Data Architecture

TBD