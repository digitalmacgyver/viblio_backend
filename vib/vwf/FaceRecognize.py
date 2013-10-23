#!/usr/bin/env python

import json
import pprint

from vib.vwf.VWorker import VWorker

class FaceRecognize( VWorker ):
    # This line controls how we interact with SWF, and changes here
    # must be made in coordination with VPWorkflow.py
    task_name = 'FaceRecognize'
    
    def run_task( self, options ):
        '''Perform the face recognition logic with the input of the
        Python options dictionary.  Return a Python dictionary with
        the agreed upon stuff in it.

        NOTE: The size of the return value is limited to 32 kB
        '''

        return {}

