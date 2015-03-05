#!/usr/bin/env python

import time

import logging
logger = logging.getLogger( __name__ )

def timer( timed ):
    def inner( *args, **kwargs ):
        start = time.time()
        result = timed( *args, **kwargs )
        end = time.time()
        logger.debug( "TIMING OUTPUT Function %s.%s took: %f" % ( timed.__module__, timed.__name__, end - start ) )
        return result
    return inner
