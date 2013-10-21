#!/usr/bin/env python

import json
import pprint

from vib.vwf.VWorker import VWorker

class FaceRecognize( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VideoProcessorWorkflow.py
    task_name = 'FaceRecognize'
    
    def run_task( self, options ):
        '''Perform the face recognition logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''
        print "Face recognition inputs are:"
        pp = pprint.PrettyPrinter( indent=4 )
        pp.pprint( options )
        print "Doing face recognition stuff!"
        return { 'media_uuid' : 1234, 'people' : { 'x' : 'y', 'a' : 'b' } }

