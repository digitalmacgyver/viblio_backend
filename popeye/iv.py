import datetime
import sys
import requests
import hashlib
import iv_config

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

def open_session():
    raw_date = datetime.datetime.now(iv_config.time_zone)
    formatted_date = raw_date.strftime('%a, %d %b %Y %H:%M:%S %Z')  
    url = iv_config.iv_host + 'session'
    session_xml = '<?xml version="1.0"?>\r\n<session xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<partnerId>VIBLIO</partnerId>\r\n<apiKey>AAA111BBB222</apiKey>\r\n<localId>9876543210</localId>\r\n</session>\r\n'
    headers = {'Content-Type':'text/xml', 'Date':formatted_date}
    r = requests.post(url, data=session_xml, headers=headers)
    print r, r.content
    if r.status_code == requests.codes.ok:
        print r.content
        soup = BeautifulSoup(r.content, 'lxml')
        try:
            session_key = str(soup.find('sessionkey').text)
            session_secret = str(soup.find('sessionsecret').text)
            print ('Received Key: ' + session_key + 'and Secret: '+ session_secret)
            session_info = {'key': session_key, 'secret': session_secret}
            return(session_info)
        except:
            print('Failed to extract session info')
            return ('False')

## compute hashed values for subsequent API calls
def generate_headers(session_info):
    session_key = session_info['key']
    session_secret = session_info['secret']
    ## Compute and format date
    raw_date = datetime.datetime.now(iv_config.time_zone)
    formatted_date = raw_date.strftime('%a, %d %b %Y %H:%M:%S %Z')
    sha_instance = hashlib.sha1()
    sha_instance.update(iv_config.partner_id + formatted_date)
    hashed_partner_id = sha_instance.hexdigest()
    sha_instance = hashlib.sha1()
    sha_instance.update(iv_config.local_id + formatted_date)
    hashed_local_id = sha_instance.hexdigest()
    sha_instance = hashlib.sha1()
    sha_instance.update(session_secret + formatted_date)
    hashed_session_secret = sha_instance.hexdigest()    
    headers = {'Content-Type': 'text/xml', 'Date': formatted_date, 'sessionKey': session_key, 'sessionSecret': hashed_session_secret, 'partnerId': hashed_partner_id, 'localId': hashed_local_id}
    print headers
    return(headers)

## Close session API
def close_session(session_info):
    url = iv_config.iv_host + 'endSession'
    headers = generate_headers(session_info)
    r = requests.delete(url, headers=headers)
    if r.status_code == requests.codes.ok:
        print 'session closed' + r.content
    else:
        print "error" + r.content


## Register User API
url = iv_host + 'user'
register_xml = '<user xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<name>Bidyut Parruck</name>\r\n<loginName>bp001</loginName>\r\n<password>12345678</password>\r\n<metadata>\r\n\t<email>bparruck@gmail.com</email>\r\n\t<contactno>408-728-8130</contactno>\r\n</metadata>\r\n</user>\r\n'

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

r = requests.post(url, data=register_xml, headers=headers)
if r.status_code == requests.codes.ok
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    description = tree.find('Description')
    print status.text, description.text
else:
    print "error"


## Login API
def login(session_info):
    url = iv_config.iv_host + 'user/login'
    headers = generate_headers(session_info)
    login_xml = '<login xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<loginName>bp001</loginName>\r\n<password>12345678</password>\r\n</login>'
    r = requests.post(url, data=login_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
                user_id = str(soup.id.text)
                print user_id
                return (user_id)
        else:
            print "Error: ", r.content


## Get User Details API
url = iv_config.iv_host + 'user/' + user_id + '/getUser'

r = requests.get(url, headers=headers)
if r.status_code == requests.codes.OK:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    print status.text
else:
    print "Error" + r.content

## Logout user API
url = iv_host + 'user/' + userId + '/logout'

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

r = requests.get(url, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    print status.text
else:
    print "Error" + r.content

## Analyze face API
def analyze(session_info, user_id, media_url):
    url = iv_config.iv_host + 'user/' + user_id + '/analyzeFaces'
    analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + user_id + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=analyze_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if str(soup.result.status.text) == 'Success':
            file_id = str(soup.result.fileid.text)
            wait_time = str(soup.result.expectedwaitseconds.text)
            print 'Success, file_id = ' + file_id + ', wait_time= ' + wait_time
            return(file_id)
    else: print 'Failed: ' + str(soup)

<html><body><result><status>Success</status><fileid>4</fileid><expectedwaitseconds>69</expectedwaitseconds></result></body></html>

## Retrieve Faces API
def retrieve(session_info, user_id, file_id):
    url = iv_config.iv_host + 'user/' + user_id + '/retrieveFaces?fileID=' + file_id 
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if str(soup.result.status.text) == 'Success':
            for url in soup.findAll('bestfaceframe'):
                file_name = str(url.text.split('/')[-1])
                with open('/mnt/uploaded_files/' + file_name, 'wb') as handle:
                    request = requests.get(url.text)
        return(soup)
    
>>> r.content
<?xml version="1.0"?>
<Result><Status>Success</Status><ExpectedWaitSeconds>0</ExpectedWaitSeconds><Tracks><NumberOfTracks>1</NumberOfTracks><Track><TrackId>0</TrackId><PersonId>-1</PersonId><BestFaceFrame>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam5_16-08-2013_14-40-14-236_0.bmp</BestFaceFrame><StartTime>2013-08-16 14:40:14</StartTime><EndTime>2013-08-16 14:40:14</EndTime><Width>229</Width><Height>229</Height><FaceCenterX>308</FaceCenterX><FaceCenterY>183</FaceCenterY><DetectionScore>36</DetectionScore><RecognitionConfidence>0.00</RecognitionConfidence></Track></Tracks></Result>


>>> soup
<html><body><result><status>Success</status><expectedwaitseconds>0</expectedwaitseconds><tracks><numberoftracks>4</numberoftracks><track><trackid>0</trackid><personid>0</personid><bestfaceframe>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam4_17-08-2013_21-42-36-833_0.bmp</bestfaceframe><starttime>2013-08-16 14:29:46</starttime><endtime>2013-08-16 14:29:46</endtime><width>192</width><height>192</height><facecenterx>271</facecenterx><facecentery>183</facecentery><detectionscore>61</detectionscore><recognitionconfidence>75.84</recognitionconfidence></track><track><trackid>2</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam4_16-08-2013_14-29-59-908_2.bmp</bestfaceframe><starttime>2013-08-16 14:29:59</starttime><endtime>2013-08-16 14:30:00</endtime><width>83</width><height>83</height><facecenterx>353</facecenterx><facecentery>325</facecentery><detectionscore>5</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track><track><trackid>3</trackid><personid>0</personid><bestfaceframe>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam4_27-08-2013_15-02-16-554_3.bmp</bestfaceframe><starttime>2013-08-16 14:30:01</starttime><endtime>2013-08-16 14:30:01</endtime><width>196</width><height>196</height><facecenterx>396</facecenterx><facecentery>170</facecentery><detectionscore>12</detectionscore><recognitionconfidence>79.23</recognitionconfidence></track><track><trackid>5</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam4_16-08-2013_14-30-11-737_5.bmp</bestfaceframe><starttime>2013-08-16 14:30:11</starttime><endtime>2013-08-16 14:30:11</endtime><width>168</width><height>168</height><facecenterx>114</facecenterx><facecentery>153</facecentery><detectionscore>30</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track></tracks></result></body></html>
>>> 

## Add Person API
def add_person():
    url = iv_config.iv_host + 'user/' + user_id + '/addPerson'
    add_person_xml = '<personDetails xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><firstName>Bhupesh</firstName><lastName>Bansal</lastName><description>Friend</description></personDetails>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=add_person_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if str(soup.result.status.text) == 'Success':
            person_id = str(soup.Person.Id.text)
    print status.text, r.content
else:
    print "Error"

>>> r.content
'<?xml version="1.0"?>\r\n<Person><Status>Success</Status><Id>0</Id></Person>\r\n'

## Train Person API
url = iv_host + 'user/' + userId + '/trainPerson?personID=' + personId + '&trackID=' + trackId + '&fileID=' + fileId

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + userId + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'

r = requests.post(url, data=analyze_xml, headers=headers)

>>> r.content
'<?xml version="1.0"?>\r\n<Result><Status>Success</Status></Result>\r\n'


>>> for x in soup.findAll('bestfaceframe'):
...     print x.text
... 
http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam5_16-08-2013_14-40-14-236_0.bmp
>>> 


session_info = open_session()
user_id = login(session_info)
media_url = 'http://s3-us-west-2.amazonaws.com/viblio-iv-test/test2.avi'
file_id = analyze(session_info, user_id, media_url)
x = retrieve(session_info, user_id, file_id)
close_session(session_info)






