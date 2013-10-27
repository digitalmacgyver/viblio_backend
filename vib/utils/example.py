#!/usr/bin/python

import logging
import sys
import time

from vib.utils import Serialize

import vib.config.AppConfig

config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

log = logging.getLogger( __name__ )
screen_output = logging.StreamHandler( sys.stdout )
log.addHandler( screen_output )

# Create a serialization object.
# We create a locking object for the example app
# For the user_uuid object
# And identify ourselves as locking_process
# We provide the popeye config
# Heartbeat our ownership of the lock every 5 seconds

# NOTE: This is an example set of parameters, in an actual usage the
# heartbeat and deployment parameters should be much higher.
s1 = Serialize.Serialize( app         = 'example', 
                         object_name = 'user_uuid', 
                         owner_id    = 's1', 
                         app_config  = config, 
                         heartbeat   = 5 )

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
                          heartbeat   = 5 )

# Acquire a lock.
print "Attempting to re-acquire the lock with s2, this will fail."
print "Call to acquire returned:", s2.acquire( blocking=False )

print "Releasing the lock with s1."
s1.release()

print "Now s2 can acquire the lock."
print "Call to acquire returned:", s2.acquire( blocking=False )

# Attempt to acquire a third, blocking lock on the same object, with a
# timeout of 15 seconds this will fail (since s1 holds the lock).
s3 = Serialize.Serialize( app         = 'example', 
                          object_name = 'user_uuid', 
                          owner_id    = 's3', 
                          app_config  = config, 
                          heartbeat   = 5,
                          timeout     = 15 )

# Acquire a lock.
print "Attempting to re-acquire the lock with s3, this will fail after the timeout of 15 seconds"
print "Call to acquire returned:", s3.acquire( blocking=True )

print "Releasing the lock with s2."
s2.release()

print "Now s3 can acquire the lock."
print "Call to acquire returned: ", s3.acquire()

print "Releasing the lock with s3."
s3.release()

s4 = Serialize.Serialize( app         = 'example', 
                          object_name = 'user_uuid', 
                          owner_id    = 's4', 
                          app_config  = config, 
                          expirey     = 10 )

print "Acquire a lock s4 with an expiration in 10 seconds."
print "Call to acquire returned:", s4.acquire()


s5 = Serialize.Serialize( app         = 'example', 
                          object_name = 'user_uuid', 
                          owner_id    = 's5', 
                          app_config  = config, 
                          expirey     = 10 )

print "Acquire a lock s5 when s4's lock expires."
print "Call to acquire returned:", s5.acquire()

sys.exit()

