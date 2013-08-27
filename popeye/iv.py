import datetime
import pytz
import sys
import requests
import hashlib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


## Define parameters
partner_id = 'VIBLIO'
local_id = '9876543210'
iv_host = 'http://71.6.45.227/FDFRRstService/RestService.svc/'
time_zone = pytz.timezone("GMT")

## Compute and format date
raw_date = datetime.datetime.now(time_zone)
formatted_date = raw_date.strftime('%a, %d %b %Y %H:%M:%S %Z')

## Open session API
url = iv_host + 'session'
session_xml = '<?xml version="1.0"?>\r\n<session xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<partnerId>VIBLIO</partnerId>\r\n<apiKey>AAA111BBB222</apiKey>\r\n<localId>9876543210</localId>\r\n</session>\r\n'
headers = {'Content-Type':'text/xml', 'Date':formatted_date}

r = requests.post(url, data=session_xml, headers=headers)

if r.status_code == requests.codes.ok:
    soup = BeautifulSoup(r.content, 'lxml')
    try:
        session_key = str(soup.find('sessionkey').text)
        session_secret = str(soup.find('sessionsecret').text)
        print session_Key, session_secret
    except:
        sys.exit()    
## compute hashed values for subsequent API calls
sha_instance = hashlib.sha1()
sha_instance.update(partner_id + formatted_date)
hashed_partner_id = sha_instance.hexdigest()
    
sha_instance = hashlib.sha1()
sha_instance.update(local_id + formatted_date)
hashed_local_id = sha_instance.hexdigest()

sha_instance = hashlib.sha1()
sha_instance.update(session_secret + formatted_date)
hashed_session_secret = sha_instance.hexdigest()

headers = {'Content-Type': 'text/xml', 'Date': formatted_date, 'sessionKey': session_key, 'sessionSecret': hashed_session_secret, 'partnerId': hashed_partner_id, 'localId': hashed_local_id}


## Close session API
url = iv_host + 'endSession'


r = requests.delete(url, headers=headers)
if r.status_code == requests.codes.ok:
    print 'session closed'
else:
    print "error"


## Register User API
url = iv_host + 'user'
register_xml = '<user xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<name>Bidyut Parruck</name>\r\n<loginName>bp001</loginName>\r\n<password>12345678</password>\r\n<metadata>\r\n\t<email>bparruck@gmail.com</email>\r\n\t<contactno>408-728-8130</contactno>\r\n</metadata>\r\n</user>\r\n'

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

r = requests.post(url, data=register_xml, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    description = tree.find('Description')
    print status.text, description.text
else:
    print "error"


## Login API
url = iv_host + 'user/login'
login_xml = '<login xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo">\r\n<loginName>bp001</loginName>\r\n<password>12345678</password>\r\n</login>'

r = requests.post(url, data=login_xml, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    if (status.text == 'Success'):
        Id = tree.find('Id')
        userId = Id.text
    print status.text, Id.text
else:
    print "Error: ", r.content


## Get User Details API
url = iv_host + 'user/' + userId + '/getUser'

r = requests.get(url, headers=headers)
if r.status_code == requests.codes.ok:
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
url = iv_host + 'user/' + userId + '/analyzeFaces'
media_url = 'http://s3-us-west-2.amazonaws.com/viblio-iv-test/test1.avi'

analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + userId + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

r = requests.post(url, data=analyze_xml, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    Id = tree.find('fileId')
    fileId = Id.text
    print r.content
else:
    print "Error"

>>> r.content
'<result><status>Success</status><fileId>2</fileId><description>File Downloading Started</description></result>'

## Retrieve Faces API
url = iv_host + 'user/' + userId + '/retrieveFaces?fileID=' + fileId 

r = requests.get(url, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    print status.text
else:
    print "Error/n" + r.content

>>> r.content
<?xml version="1.0"?>
<Result><Status>Success</Status><ExpectedWaitSeconds>0</ExpectedWaitSeconds><Tracks><NumberOfTracks>1</NumberOfTracks><Track><TrackId>0</TrackId><PersonId>-1</PersonId><BestFaceFrame>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam5_16-08-2013_14-40-14-236_0.bmp</BestFaceFrame><StartTime>2013-08-16 14:40:14</StartTime><EndTime>2013-08-16 14:40:14</EndTime><Width>229</Width><Height>229</Height><FaceCenterX>308</FaceCenterX><FaceCenterY>183</FaceCenterY><DetectionScore>36</DetectionScore><RecognitionConfidence>0.00</RecognitionConfidence></Track></Tracks></Result>

## Add Person API
url = iv_host + 'user/' + userId + '/addPerson'

add_person_xml = '<personDetails xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><firstName>Bhupesh</firstName><lastName>Bansal</lastName><description>Friend</description></personDetails>'

headers = {'Content-Type': 'text/xml', 'Date': date, 'sessionKey': sessionKey.text, 'sessionSecret': hashed_sessionSecret, 'partnerId': hashed_partnerId, 'localId': hashed_localId}

r = requests.post(url, data=add_person_xml, headers=headers)
if r.status_code == requests.codes.ok:
    tree = ET.fromstring(r.content)
    status = tree.find('Status')
    Id = tree.find('Id')
    PersonId = Id.text
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






