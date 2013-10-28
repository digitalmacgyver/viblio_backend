#!/usr/bin/env python

import os
os.environ['BOTO_CONFIG'] = os.path.dirname( __file__ ) + '../config/boto.config'
from optparse import OptionParser
import sys

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

from vib.thirdParty.mturkcore import MechanicalTurk

def assign_qualification( worker_id ):
    mt = MechanicalTurk( 
        { 
            'use_sandbox'           : True, 
            'stdout_log'            : True, 
            'aws_key'     : config.awsAccess,
            'aws_secret_key' : config.awsSecret
            }  )
    
    options = {
        'QualificationTypeId' : config.ViblioQualificationTypeId,
        'WorkerId' : worker_id,
        'IntegerValue' : 100,
        'SendNotification' : True
        }

    result = mt.create_request( 'AssignQualification', options )

    print "Result was: %s" % result


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option( '-w', '--worker',
                       dest="worker_id",
                       help="The Worker ID of the Mechanical Turk Worker" )

    ( options, args ) = parser.parse_args()

    if not ( options.worker_id and len( options.worker_id ) ):
        parser.print_help()
        sys.exit( 0 )
    else:
        print "Assigning qualification %s to worker %s" % ( config.ViblioQualificationTypeId, options.worker_id )
        assign_qualification( options.worker_id )
