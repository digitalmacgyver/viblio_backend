#!/usr/bin/env python

import boto.swf
import boto.swf.layer2 as swf
import boto.ec2.cloudwatch as cloudwatch
import CheckerUtils
import json
import logging
from logging import handlers
import pdb
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

logger = logging.getLogger( __name__ )
logger.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'vwf: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )

consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

logger.addHandler( syslog )
logger.addHandler( consolelog )

import vib.vwf.VPWorkflow
from vib.vwf.VPWorkflow import VPW

class Monitor( swf.Domain ):

    def __init__( self, **kwargs ):
        self.domain    = vib.vwf.VPWorkflow.domain
        self.name      = self.domain
        self.version   = vib.vwf.VPWorkflow.version

        super( Monitor, self ).__init__( **kwargs )

        self.logger = logger
        self.cw = cloudwatch.connect_to_region( config.cloudwatch_region )

    def print_queue_depths( self ):
        for stage in sorted( VPW.keys() ):
            print "%s (%s) had %s outstanding tasks." % ( stage, VPW[stage]['task_list'] + config.VPWSuffix + config.UniqueTaskList, self.count_pending_activity_tasks( VPW[stage]['task_list'] + config.VPWSuffix + config.UniqueTaskList )['count'] )

    def update_cloudwatch( self ):
        for stage in sorted( VPW.keys() ):
            self.cw.put_metric_data( config.swf_domain, 
                                     config.swf_queue_metric, 
                                     self.count_pending_activity_tasks( VPW[stage]['task_list'] + config.VPWSuffix + config.UniqueTaskList )['count'],
                                     unit       = 'Count',
                                     dimensions = { 'Stage' : stage,
                                                    'Deployment' : config.VPWSuffix
                                                    }
                                     )

    

    
    def set_queue_depth_for_scaling(self):
        trans_name = self.task_list_name('Transcode', VPW, config)
        faced_name = self.task_list_name('FaceDetect', VPW, config)
        dom = config.swf_domain
        ntrans = self.count_pending_activity_tasks(trans_name)['count']
        nfaced = self.count_pending_activity_tasks(faced_name)['count']
        mx = max(ntrans, nfaced)
        self.cw.put_metric_data(dom, 'queue_depth_for_scaling', mx, dimensions = { 'Deployment' : config.VPWSuffix })

    def task_list_name(self, type, settings, conf):
        CheckerUtils.validate_string(type)
        CheckerUtils.validate_dict_nonempty(settings)
        CheckerUtils.validate_object(conf)

        base = settings[type]['task_list']
        suf = conf.VPWSuffix
        id = conf.UniqueTaskList
        return base + suf + id
                                     
