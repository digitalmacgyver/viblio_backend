#!/usr/bin/python

import logging
import sys
import time

import Serialize

sys.path.append("../popeye")
from appconfig import AppConfig
config = AppConfig( '../popeye/popeye' ).config()

log = logging.getLogger( __name__ )
screen_output = logging.StreamHandler( sys.stdout )
log.addHandler( screen_output )

# Create a serialization object.
# We create a locking object for the example app
# For the user_uuid object
# And identify ourselves as locking_process
# We provide the popeye config
# Heartbeat our ownership of the lock every 5 seconds
# Claim the lock even if someone else has it if it's more than 30 seconds old

# NOTE: This is an example set of parameters, in an actual usage the
# heartbeat and deployment parameters should be much higher.
s1 = Serialize.Serialize( app         = 'example', 
                         object_name = 'user_uuid', 
                         owner_id    = 's1', 
                         app_config  = config, 
                         heartbeat   = 5, 
                         timeout     = 30 )

print "To see informative messages, run in another window:"
print "tail -f ", config.logfile

# Acquire a lock.
print "Acquiring the lock with s1."
print "Call to acquire returned:", s1.acquire( blocking=True )

print "Sleeping for 10 seconds so we can see heartbeating working."
time.sleep( 10 )

# Attempt to acquire a second, nonblocking lock on the same object,
# this will fail (since s1 holds the lock).
s2 = Serialize.Serialize( app         = 'example', 
                          object_name = 'user_uuid', 
                          owner_id    = 's2', 
                          app_config  = config, 
                          heartbeat   = 5, 
                          timeout     = 30 )

# Acquire a lock.
print "Attempting to re-acquire the lock with s2, this will fail."
print "Call to acquire returned:", s2.acquire( blocking=False )

print "Releasing the lock with s1."
s1.release()

time.sleep( 5 )

print "Now s2 can acquire the lock."
print "Call to acquire returned:", s2.acquire( blocking=False )

s2.release()

sys.exit()

