#!/usr/bin/env python

from optparse import OptionParser
import os
import sys
import StringIO
import time
import traceback

import requests
import pycurl

import config
import json

#exponential backoff
initial_delay = 10 # 10 seconds
max_attempts = 3
def attempts():
    for i in range(max_attempts):
        yield i
        time.sleep(initial_delay ** i)

def die(msg, exit_code=0):
    print msg
    sys.exit(exit_code)

def upload(location, filename, offset=0, upload_speed=None):
    c = None
    content_type = "application/offset+octet-stream"
    try:
        c = pycurl.Curl()
        #c.setopt(pycurl.VERBOSE, 1)
        c.setopt(pycurl.URL, str(location))
        bout = StringIO.StringIO()
        hout = StringIO.StringIO()

        c.setopt(pycurl.HEADERFUNCTION, hout.write)
        c.setopt(pycurl.WRITEFUNCTION, bout.write)
        c.setopt(pycurl.UPLOAD, 1)
        c.setopt(pycurl.CUSTOMREQUEST, 'PATCH')

        f = open(filename, 'rb')
        if offset > 0: 
            f.seek(offset)
        c.setopt(pycurl.READFUNCTION, f.read)
        filesize = os.path.getsize(filename)
        if upload_speed:
            c.setopt(pycurl.MAX_SEND_SPEED_LARGE, upload_speed)
        c.setopt(pycurl.INFILESIZE, filesize - offset)
        c.setopt(pycurl.HTTPHEADER, ["Expect:", "Content-Type: %s" % content_type, "Offset: %d" % offset])
        c.perform()

        response_code = c.getinfo(pycurl.RESPONSE_CODE)
        response_data = bout.getvalue()
        response_hdr = hout.getvalue()
        #print "DATA", response_data
        #print response_hdr
        #print "patch->", response_code
        return response_code == 200
    finally:
        if c: c.close()

parser = OptionParser()
parser.add_option("-f", "--file", dest="filename",
                  help="file to upload")
parser.add_option("-u", "--upload_speed",
                  dest="upload_speed", default=None,
                  help="upload speed in bytes per second")

parser.add_option("-e", "--email",
                  dest="email",
                  help="email address for authentication")
parser.add_option("-p", "--password",
                  dest="password",
                  help="password for authentication")
parser.add_option("-r", "--realm",
                  dest="realm", default="db",
                  help="authentication realm: db or facebook")

"""
parser.add_option("-t", "--content-type",
                  dest="content_type", default="binary/octet-stream",
                  help="content-type")
"""

(options, args) = parser.parse_args()


if not options.filename:
    parser.print_help()
    sys.exit(0)

if not options.email:
    parser.print_help()
    sys.exit(0)

if not options.password:
    parser.print_help()
    sys.exit(0)

upload_speed = None
try:
    if options.upload_speed:
        upload_speed = int(options.upload_speed)
except:
    parser.print_help()
    sys.exit(0)    

c = requests.get( config.AUTH_ENDPT, params={'email': options.email, 'password': options.password, 'realm': options.realm } )
if c.status_code != 200:
    die("failure to connect to %s: %s" % config.AUTH_ENDPT, c.reason )
r = json.loads( c.content )
if 'error' in r:
    die("failure to authenticate: %s" % r['message'] )
UUID = r['user']['uuid']

os.system( "/usr/local/bin/ffprobe -v quiet -print_format json=c=1 -show_format -show_streams %s > /tmp/md.json" % options.filename )
with open("/tmp/md.json","r") as myfile:
    data=myfile.read()
md=json.loads(data)
md['uuid'] = UUID
md['file'] = { 'Path': options.filename };

print( 'Uploading media file for user: %s' % UUID )

filename = options.filename
filesize = os.path.getsize(filename)

payload = json.dumps(md)

c  = requests.post(config.CREATE_ENDPT, headers={"Final-Length": filesize}, data=payload)

if c.status_code != 201:
    die("create failure. reason: %s"  % c.reason)

location = c.headers["Location"]
print location

def get_offset(location):
    h = requests.head(location)
    print h.headers
    offset = int(h.headers["Offset"])
    print "Offset: ", offset
    return offset 


status = "upload failure"
offset = 0
for i in attempts():
    try:
        offset = get_offset(location)
        if offset == filesize:
            status = "upload success"
            break
        upload(location, filename, offset=offset, upload_speed=upload_speed)
        offset = get_offset(location)
        if offset == filesize:
            status = "upload success"
            break
    except:
        traceback.print_exc()
die(status)