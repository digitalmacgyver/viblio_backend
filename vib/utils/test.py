#!/usr/bin/python

import logging
import sys
import time

from vib.utils import Serialize

import vib.config.AppConfig

config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

expireys = [None, 5]
heartbeats = [None, 5]
timeouts = [1, 20]
blockings = [True, False]

for e in expireys:
    for h in heartbeats:
        for t in timeouts:
            for b in blockings:
                print "Expirey=%s\tHeartbeat=%s\tTimeout=%s\tBlocking=%s" % ( e, h, t, b )
                s1 = Serialize.Serialize( 'foo', 'bar', 'baz-s1', config, e, h, t )
                print "Result of s1 acquire:", s1.acquire()
                s2 = Serialize.Serialize( 'foo', 'bar', 'baz-s2', config, e, h, t )
                print "Result of s2 acquire:", s2.acquire( blocking=b )
                s3 = Serialize.Serialize( 'foo', 'bar', 'baz-s3', config, e, h, t )
                print "Result of s3 acquire:", s3.acquire( blocking=not b)
                #s1.release()
                #s2.release()
                #s3.release()
        

# Heartbeating, Blocking, Timeout, Expirey


# Heartbeating, Blocking
# Get a lock where none exists.
# DONE
# Get a lock where an old one exists with NULL as owner_id.
# DONE
# Get a lock where the current owner already owns it.
# DONE
# Get a lock where the timeout has already occured.
# DONE
# Get a lock where we have to wait for the timeout.
# Done

# Heartbeating, Nonblocking
# Get a lock where none exists.
# DONE 
# Get a lock where an old one exists with NULL as owner_id.
# DONE
# Get a lock where the current owner already owns it.
# DONE 
# Get a lock where the timeout has already occured.
# DONE
# Get a lock where we have to wait for the timeout.
# DONE

# No Heartbeating, Blocking
# Get a lock where none exists.
# DONE
# Get a lock where an old one exists with NULL as owner_id.
# DONE
# Get a lock where the current owner already owns it.
# DONE 
# Get a lock where the timeout has already occured.
# DONE
# Get a lock where we have to wait for the timeout.
# DONE 

# No Heartbeating, NonBlocking
# Get a lock where none exists.
# Get a lock where an old one exists with NULL as owner_id.
# Get a lock where the current owner already owns it.
# Get a lock where the timeout has already occured.
# Get a lock where we have to wait for the timeout.

# Check some stuff with no timeout.

# T
