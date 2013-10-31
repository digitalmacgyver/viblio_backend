#!/usr/bin/env python

import json
import logging
from logging import handlers
import requests
import time

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

logger = logging.getLogger( 'vib.fb.CreateContacts' )
logger.setLevel( logging.DEBUG )

syslog = logging.handlers.SysLogHandler( address="/dev/log" )

format_string = 'fb: { "name" : "%(name)s", "module" : "%(module)s", "lineno" : "%(lineno)s", "funcName" : "%(funcName)s",  "level" : "%(levelname)s", "deployment" : "' + config.VPWSuffix + '", "activity_log" : %(message)s }'

sys_formatter = logging.Formatter( format_string )

syslog.setFormatter( sys_formatter )
syslog.setLevel( logging.INFO )
consolelog = logging.StreamHandler()
consolelog.setLevel( logging.DEBUG )

logger.addHandler( syslog )
logger.addHandler( consolelog )

rekog_api_key = 'UpNFfyP7ttEhxya5'
rekog_api_secret = 'b37NhBxCcbSC7LQ5'

fb_access_token = 'CAAGwcWaZA3SsBANSdWla6CVeIJ5NeFI4ai3OQeZAwQHV2aVCzZC4HkZAZACC3yLj1is6816LkiQTLKfTkP2rlXwcTOdHigAwt6GcppIA7NzWFu4qIkVkQQkzjxMYX6xzEWWplp63EomqtWWbVaDyzjVxzNSymKselb1RXbOTZCZA5sMkgtyDcZBlFURo4dRdz5wZD'

namespace = "facebook_demo"

user_id = 'trial_' + str( time.time() )

fb_user = '100006092460819'
fb_friends = [ '621782016', '100005828619719' ]

#user_uuid = '08CC5BC0-3856-11E3-BF24-4155F9A9DC35'

def face_crawl( fb_user, fb_friends ):
    
    jobs = 'face_crawl_[' + fb_user
    for fb_id in fb_friends:
        jobs += ';' + fb_id
    jobs += ']'

    #jobs = "face_crawl_['621782016']"

    print "Face crawl jobs is", jobs
        
    data = {
        'api_key'      : rekog_api_key,
        'api_secret'   : rekog_api_secret,
        'jobs'         : jobs,
        'fb_id'        : fb_user,
        'access_token' : fb_access_token,
        'name_space'   : namespace,
        'user_id'      : user_id
        }

    print "%s" % data

    r = requests.post( "http://rekognition.com/func/api/", data )
    return r.json()

result = face_crawl( fb_user, [] )#fb_friends )
print result
