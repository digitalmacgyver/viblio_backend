#!/usr/bin/env python

from optparse import OptionParser
import os
import sys
import StringIO
import time
import traceback

import requests
import pycurl

import json
import Cookie

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

def parse_cookies(hdr):
    C = Cookie.SimpleCookie()
    C.load( hdr )
    return C

def aws_cookie( cookies ):
    return "AWSELB=%s" % cookies['AWSELB'].value

chunk_size = 256 * 1024;
def upload(location, filename, offset=0, upload_speed=None, cookie=None):
    content_type = "application/offset+octet-stream"
    filesize = os.path.getsize(filename)
    f = open(filename, 'rb')
    if offset > 0: 
        f.seek(offset)
    to_read = chunk_size
    if ( (filesize - offset) < to_read ):
        to_read = filesize - offset
    fdata = f.read( to_read );
    f.close();
    print "PATCH %s offset=%d, len=%d" % ( location, offset, len(fdata) )
    headers = {"Expect": None, 
               "Content-Type": content_type, 
               "Content-Length": len(fdata), 
               "Offset": offset}
    if ( cookie ):
        headers["Cookie"] = cookie
    c = requests.patch( location, verify=False, data=fdata, headers=headers )
        
    return c.status_code == 200

cdb = {
    'local': {
        'auth': 'https://localhost/services/na/authenticate',
        'server': 'https://localhost/files'
        },
    'staging': {
        'auth': 'https://staging.viblio.com/services/na/authenticate',
        'server': 'https://staging.viblio.com/files'
        },
    'prod': {
        'auth': 'https://prod.viblio.com/services/na/authenticate',
        'server': 'https://upload.viblio.com/files'
        },
    'uploader': {
        'auth': 'https://prod.viblio.com/services/na/authenticate',
        'server': 'https://uploader.viblio.com/files'
        }
    }

parser = OptionParser()
parser.add_option("-f", "--file", dest="filename",
                  help="file to upload")
parser.add_option("-u", "--upload_speed",
                  dest="upload_speed", default=None,
                  help="upload speed in bytes per second")

parser.add_option("-a", "--auth",
                  dest="auth",
                  help="auth server: local, staging or prod")
parser.add_option("-s", "--server",
                  dest="server",
                  help="upload server: local, staging, prod or uploader")
parser.add_option("-S", "--Server",
                  dest="manual",
                  help="upload server: IP address or hostname")

parser.add_option("-e", "--email",
                  dest="email",
                  help="email address for authentication")
parser.add_option("-p", "--password",
                  dest="password",
                  help="password for authentication")
parser.add_option("-r", "--realm",
                  dest="realm", default="db",
                  help="authentication realm: db or facebook")


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

if not options.auth:
    parser.print_help()
    sys.exit(0)

if not options.server and not options.manual:
    parser.print_help()
    sys.exit(0)

if options.manual:
    cdb[options.manual] = {}
    cdb[options.manual]['server'] = options.manual
    options.server = options.manual
    
upload_speed = None
try:
    if options.upload_speed:
        upload_speed = int(options.upload_speed)
except:
    parser.print_help()
    sys.exit(0)

c = requests.get( cdb[options.auth]['auth'], params={'email': options.email, 'password': options.password, 'realm': options.realm } )
if c.status_code != 200:
    die("failure to connect to %s: %s" % cdb[options.auth]['auth'], c.reason )
r = json.loads( c.content )
if 'error' in r:
    die("failure to authenticate: %s" % r['message'] )
UUID = r['user']['uuid']

md={}
if os.path.isfile( "/usr/local/bin/ffprobe" ):
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

print "posting to: " + cdb[options.server]['server']

c = requests.post(cdb[options.server]['server'], verify=False, headers={"Final-Length": filesize}, data=payload)

if c.status_code != 201:
    die("create failure. reason: %s"  % c.reason)

location = c.headers["Location"]

# If the actual brewtus server is behind a https proxy,
# the location header will be http://, but we need to
# access it through https:// if that is our server
if ( cdb[options.server]['server'].startswith('https:') and
     location.startswith('http:') ):
    location = location.replace('http:', 'https:')

print "Location header is: " + location
if ( 'Set-Cookie' in c.headers ):
    cookie = c.headers["Set-Cookie"]
    print "Cookie header is: " + cookie
    cookies = parse_cookies( cookie )
    cval = aws_cookie( cookies )
    print "Cookie return is: " + cval
else:
    cval = None

def get_offset(location):
    if ( cval ):
        h = requests.head(location,verify=False,headers={"Cookie": cval})
    else:
        h = requests.head(location,verify=False)
    # print h.headers
    if ( 'Offset' in h.headers ):
        offset = int(h.headers["Offset"])
    else:
        offset = 0
    # print "Offset: ", offset
    return offset 

status = "upload failure"
offset = 0
while( offset < filesize ):
    for i in attempts():
        if ( upload(location, filename, offset=offset, upload_speed=upload_speed, cookie=cval) ):
            break
    offset = get_offset(location)
    if offset == filesize:
        status = "upload success"
        break 
die(status)

