Facebook Integration
====================

This package holds code for interacting with Facebook.

Contact Creation
----------------

The [CreateContacts](./CreateContacts.py) module is responsible for synchronising a Viblio user's contact list with their Facebook freind list, and collecting face images of those freinds for both machine vision recognition, and display with the contacts.

* Reads from Amazon [SQS](http://aws.amazon.com/sqs/) queue via [boto.sqs](http://boto.readthedocs.org/en/latest/ref/sqs.html) - the queue name is control ed via configuration and differs in local, staging, and production
  * Receives messages sent to this queue by the CAT webserver, which include a JSON dictionary with keys including:
    * facebook_id - The Facebook ID of a user who has linked their Viblio account with Facebook
    * fb_access_token - an OAUTH token for the Facebook id in question with the requisite user_photos and friends_photos permissions
    * user_uuid - The Viblio user_uuid of the user
* Accesses the [Facebook Graph API](https://developers.facebook.com/docs/graph-api/) and extracts the user's friend list
* Calls the ReKognition [FaceCrawl](http://rekognition.com/developer/docs#facecrawl) method for any Facebook Friends who are not already Viblio contacts
* Creates new Viblio contacts for the user_uuid for each of their Facebook friends with the names provided by Facebook, and images provided by ReKognition

At the end of the operation, any Facebook friends not previously
associated with the account have:
* A Contact row in our [database](../../schema/README.md)
  * A contact_name from Facebook
  * A provider value of 'facebook'
  * A provider_id of that contact's facebook ID
  * A user_id corresponding to the user.id of the user.uuid we were passed
  * A picture_uri that refers to an S3 location of a black and white face photo of that person extracted by ReKognition from Facebook

Within ReKognition a user is created for the Viblio user_uuid, who has
contacts named the Facebook ID's of the people in question.

Wrapper Script and Deployment
-----------------------------

The simple CreateContacts-wrapper.py is managed via supervisor in our
[configuration](../config/README.md).  