#!/usr/bin/env python

import os
os.environ['BOTO_CONFIG'] = os.path.dirname( __file__ ) + '../config/boto.config'
from optparse import OptionParser
import sys

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

from vib.thirdParty.mturkcore import MechanicalTurk

def foo():
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            'aws_key'     : config.awsAccess,
            'aws_secret_key' : config.awsSecret
            }  )
    
    options = {
        'Title' : 'Recognize Faces and Merge Tracks',
        'Description' : 'Identify and match pictures of faces.',
        'Reward' : {
            'Amount' : 0,
            'CurrencyCode' : 'USD'
            },
        'AssignmentDurationInSeconds' : 60*60,
        'Keywords' : 'oilbiv',
        'AutoApprovalDelayInSeconds' : 0,
        'QualificationRequirement' : {
            'QualificationTypeId' : config.ViblioQualificationTypeId,
            'Comparator' : 'Exists'
            }
        }

    result = mt.create_request( 'RegisterHITType', options )

    print "Result was: %s" % result


foo()
