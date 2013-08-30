import datetime
import sys
import requests
import hashlib
import iv_config
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
def register_user(session_info, uid):
    url = iv_config.iv_host + 'user'
    sha_instance = hashlib.sha1()
    sha_instance.update(uid)
    password = sha_instance.hexdigest()
    register_xml = '<user xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><name>' + uid + '</name><loginName>' + uid + '</loginName><password>' + password '</password><metadata><email>bparruck@gmail.com</email><contactno>408-728-8130</contactno></metadata></user>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=register_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
                user_id = str(soup.id.text)
                print user_id
                return (user_id)
        else:
            print "Error: ", r.content

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
def get_user_details(session_info, user_id):
    url = iv_config.iv_host + 'user/' + user_id + '/getUser'
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
                user_id = str(soup.id.text)
                print user_id
                return (user_id)
        else:
            print "Error: ", r.content

## Logout user API
def logout(session_info, user_id):
    url = iv_config.iv_host + 'user/' + user_id + '/logout'
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
            print r.content
            return (user_id)
        else:
            print "Error: ", r.content

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
## <html><body><result><status>Success</status><fileid>4</fileid><expectedwaitseconds>69</expectedwaitseconds></result></body></html>

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
##<Result><Status>Success</Status><ExpectedWaitSeconds>0</ExpectedWaitSeconds><Tracks><NumberOfTracks>1</NumberOfTracks><Track><TrackId>0</TrackId><PersonId>-1</PersonId><BestFaceFrame>http://71.6.45.227/FDFRRstService/Detected/FACES/FDFR_Cam5_16-08-2013_14-40-14-236_0.bmp</BestFaceFrame><StartTime>2013-08-16 14:40:14</StartTime><EndTime>2013-08-16 14:40:14</EndTime><Width>229</Width><Height>229</Height><FaceCenterX>308</FaceCenterX><FaceCenterY>183</FaceCenterY><DetectionScore>36</DetectionScore><RecognitionConfidence>0.00</RecognitionConfidence></Track></Tracks></Result>

## Add Person API
def add_person(session_info, first_name, last_name):
    url = iv_config.iv_host + 'user/' + user_id + '/addPerson'
    add_person_xml = '<personDetails xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><firstName>' + first_name + '</firstName><lastName>' + last_name + '</lastName><description>Friend</description></personDetails>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=add_person_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if str(soup.result.status.text) == 'Success':
            person_id = str(soup.Person.Id.text)
            print status.text, r.content
        else:
            print "Error"
#'<?xml version="1.0"?>\r\n<Person><Status>Success</Status><Id>0</Id></Person>\r\n'

def train_person(session_info, user_id, person_id, track_id, file_id, media_url):
    url = iv_host + 'user/' + user_id + '/trainPerson?personID=' + person_id + '&trackID=' + track_id + '&fileID=' + file_id
    analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + user_id + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=analyze_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print soup
        if str(soup.result.status.text) == 'Success':
            return('Success' + str(r.content))
##'<?xml version="1.0"?>\r\n<Result><Status>Success</Status></Result>\r\n'

## Main code
session_info = open_session()
user_id = login(session_info)
media_url = 'http://s3-us-west-2.amazonaws.com/viblio-iv-test/test2.avi'
file_id = analyze(session_info, user_id, media_url)
x = retrieve(session_info, user_id, file_id)

train_person(session_info, user_id, person_id, track_id, file_id, media_url)


logout(session_info, user_id)
close_session(session_info)
get_user_details(session_info, user_id)






