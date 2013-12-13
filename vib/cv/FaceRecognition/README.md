FaceRecognition
===============

Terminology
-----------

The face recognition system uses the following terminology:

* Face: An image thought to contain one face (provided via a URL)
* Contact: Each face that is added or deleted from the system is
  explicitly associated with a particular contact - this represents
  the identity of the person this face belongs to.
* User: Each contact and their associated faces are associated with
  one user.  All face recognition operations are also associated with
  one user, and consider only faces and contacts for that user.
  * Users offer a way to partition the face recognition system into
    independent pieces.
* Score: Each face added to the system must include a score.  This
  score is used by the face recognition system to identify the "best"
  faces to be used internally for recognition.  Higher values indicate
  better faces.

Efficiency / Performance
------------------------

Many of the API calls below accept arrays of faces to operate on.

When operating on several faces, providing those faces as an array to
one API call is much more efficient and will give much better
performance than iteratively calling these operations with 1 face over
and over.  This is because operations which change the recognition
system, such as adding or deleting a face, cause a "training"
operation for the recognition system, whose run time is proportional
to the total number of faces for that contact in the system - this
training operation is performed once per API call, not once per face -
so providing multiple faces per API call substantially improves
performance.

API
---

### Methods

Return values for all methods except for ```get_faces``` and the
```recogn(ize*|ition*)``` methods are described in the subsequent
section.

The [Face Data Structure](#face_data_structure) which is frequently
used as a input argument and return value is described in the section
below.

The add and delete methods have these general properties:

* Redundant calls do no harm: faces can be added or deleted multiple
  times, all attempts past the first will be ignored.

* Partial errors do not terminate execution: if a given face can't be
  added or deleted for some reason, this is noted and then the next
  face is processed.  Information about which faces were successfully
  processed are available in the return values.

All these calls globally serialize on the user in question.

* ```add_faces( user_id, contact_id, [ array of face data structures ] )```
  * Subsequent to this call, calls to ```recognize_face``` will
    consider these faces among those that identify ```contact_id```
  * ```user_id``` and ```contact_id``` are integer values provided by
    the caller specifying the user and contact that the faces in the
    array should be added to
  * If the ```user_id``` and/or ```contact_id``` are being used for
    the first time, appropriate structures are created in the
    recognition system, there are no "add_user" or "add_contact"
    methods
* ```delete_faces( user_id, contact_id, [ array of face data structures ] )```
  * Calls to ```recognize_face``` will no longer consider these faces
    among those that identify ```contact_id```
* ```delete_contact( user_id, contact_id )```
  * Delete all faces associated with the contact for the user
* ```delete_user( user_id )```
  * Delete all faces and contacts for the user, and delete the user
     itself
* ```get_faces( user_id, contact_id=None )```
  * Returns an array face data structures associated with this
    ```user_id``` and ```contact_id```
  * If ```contact_id``` is not provided, or is None, returns faces for
    all contacts associated with this user.
  * Returns None if an unexpected error occurs
* ```recognize_face( user_id, face_url )```
  * ```face_url``` is a URL to an image which is thought to contain a
    face
  * Returns either None or the following data structure
    * Returns None if no face was detected in the image at ```face_url```
    * If a face was detected, returns this data structure: ```{ 'recognize_id' : 123, 'faces' : [ array of 0-3 face data structures ] }```
      * ```recognize_id``` is an integer that is used to provide
        feedback to FaceRecognition system for reporting, see
        ```recognize_feedback``` and ```recognize_stats``` below
      * The ```faces``` key refers to a face array with 0-3 candidate
        augmented face data structures are returned in descending
        order of recognition confidence.  The face data structures are
        augmented with an additional ```recognition_confidence``` key
        which is the recognition
        confidence. ```recognition_confidence``` is a floating point
        number between 0 and 1.
* ```recognition_feedback( recognize_id, result )```
  * ```recognize_id``` is the value returned by a prior call to ```recognize_face```
  * ```result``` is either:
    * None if none of the faces from ```recognize_face``` were matches
    * 1, 2, or 3 if the 1st, 2nd, or 3rd face from
      ```recognize_face``` was a match (in the case where multiple
      faces were matches the lowest matching number should be used)
* ```recognition_stats( user_id=None )```
  * If ```user_id``` is not provided or is ```None```, stats for the
    entire system are returned, otherwise stats only for that
    ```user_id``` are returned.
  * Return value is:
    ```
    {  'recognize_calls' : 743, # The total number of recognize_face calls 
                                # for which any candidate matches were returned
       'feedback_calls'  : 367, # The number of recognize_face calls for which 
                                # recognition_feedback has been provided
       'true_positives'  : 312, # The number of successful matches made
       'false_positives' :  55, # The number of times no match was found }
    ```
    Note that ```false_positives + true_positives == feedback_falls```
* ```recognition_stat_details( user_id=None )```
  * If ```user_id``` is not provided or is ```None```, stats for the
    entire system are returned, otherwise stats only for that
    ```user_id``` are returned.
  * Returns an array of dictionary like objects with the following
    format:

    ```
    {  'id'                : 12,   # The recognition_id of this row returned from recognize_face
       'user_id'           : 443,
       'face_url'          : 'http://...', 
       'face1_id'          : 69, 
       'face1_confidence'  : 0.98,
       'face2_id'          : 69, 
       'face2_confidence'  : 0.98,
       'face3_id'          : None, 
       'face3_confidence'  : None,
       'feedback_received' : True, # Has feedback about this match been received?
       'recognized'        : True,
       'feedback_result'   : 2,    # The value of recognize_feedback's result
    }
    ```

    Notes:
      * ```face#_id|confidence``` are ```None``` if the ```recognize_face``` returned less than 3 candidate faces
      * ```feedback_result``` is ```None``` if ```recognized``` is ```False``
       
### Return Values

* All methods except get_faces and recognize_face return the following
  data structure:

```
{ 
  'added'     : [ array of added face data structures ],
  'deleted'   : [ array of deleted face data structures ],
  'unchanged' : [ array of face data structures for which no operation was performed ],
  'error'     : [ array of face data structures for which an unexpected error occurred ]
}
```

The ```unchanged``` key can occur when we are requested to add a face
that already exists, or delete a face that does not exist.

<a name="face_data_structure" />
### Face Data Structure

The face data structure is a dictionary like object with the following
keys:

*Mandatory fields set by API callers:* This set of fields is necessary
 and sufficient whenever a face data structure is called for on input.

These fields will always be included in the face data structures
returned by the various API calls.

The callers of the API must provide initial values for these fields
during ```add_faces```.

* Note: the ( user_id, contact_id, face_id ) tuple must uniquely
  identify a face
* user_id - integer value identifying the user this face is associated with
* contact_id - integer value identifying the contact this face is associated with
* face_id - integer value identifying this particular face image
* face_url - a URL to this face image
* external_id - Either None, or an integer value - this is a
  convenience variable that allows a caller of the recognition API to
  label a particular face in some way meaningful to them
* score - floating point value specifying how "good" this face is,
  higher values are better - will be used by face recognition to
  select the best faces to use for matching

*Public fields set by the Recognition System:* Once a face has been added, it
 will have these additional fields (available through the return
 values from the various functions).

* id - integer value uniquely identifying this face.  This value is
  guaranteed to be unique across all faces in the recognition system
  and not to change

*Private fields set by the Recognition System:*

The Recognition System will set a number of additional fields in the
Face data structure for its own purposes, these include: l1_id,
l1_tag, l2_id, l2_tag, \_sa_instance_state, created_date, updated_date.
These values should not be relied upon or changed by API callers.


### Side Effects

Due to race conditions and errors, the face recognition system can be
in an inconsistent state at any given time.  

Best efforts are made to repair the face recognition system to a
consistent state during the course of any API call.

This means API calls can take unexpected actions as they completed the
deferred processing for previously failed operations.

Callers of the API generally need not worry about this, it is
mentioned here as a developer note and to explain why log message may
indicate unexpected operations being performed (e.g. faces being
deleted on a call to ```get_faces```).

Determinism
-----------

This module makes no guarantees about deterministic behavior with
regard to adding, deleting, or recognizing faces, for two main
reasons:

* We rely on a third party recognition system which makes no such
  guarantees
* Race conditions can arise, for example if three requests come in
  rapid sequence saying: Add face A, delete face A, add face A they
  may be executed in a different order such as Add face A, add face A
  (which is ignored), delete face A.

