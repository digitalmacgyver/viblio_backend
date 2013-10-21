#!/usr/bin/env python

import json
import pprint

import VideoWorker

class FaceDetect( VideoWorker.VideoWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VideoProcessorWorkflow.py
    task_name = 'FaceDetect'
    
    def run_task( self, options ):
        '''Perform the face detection logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''
        print "Face detection inputs are:"
        pp = pprint.PrettyPrinter( indent=4 )
        pp.pprint( options )
        print "Doing face detection stuff!"
        return { 'media_uuid' : 1234, 'tracks' : [ { 's3url' : 'blahblahblah' } ] }

