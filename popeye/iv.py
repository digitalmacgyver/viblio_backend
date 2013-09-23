import datetime
import sys
import requests
import hashlib
import iv_config
import uuid
import time
from bs4 import BeautifulSoup

def perror( log, msg ):
    log.error( msg )
    return { 'error': True, 'message': msg }

def open_session():
    raw_date = datetime.datetime.now(iv_config.time_zone)
    formatted_date = raw_date.strftime('%a, %d %b %Y %H:%M:%S %Z')  
    url = iv_config.iv_host + 'session'
    session_xml = '<?xml version="1.0"?><session xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><partnerId>VIBLIO</partnerId><apiKey>AAA111BBB222</apiKey><localId>9876543210</localId></session>'
    headers = {'Content-Type':'text/xml', 'Date':formatted_date}
    r = requests.post(url, data=session_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print str(soup)
        try:
            session_key = soup.result.sessionkey.string
            session_secret = soup.result.sessionsecret.string
            print ('session Key: ' + session_key + 'and Secret: '+ session_secret)
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
    headers = {'Content-Type': 'text/xml', 
               'Date': formatted_date, 
               'sessionKey': session_key, 
               'sessionSecret': hashed_session_secret, 
               'partnerId': hashed_partner_id, 
               'localId': hashed_local_id}
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
    register_xml = '<user xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><name>' + uid + '</name><loginName>' + uid + '</loginName><password>' + password + '</password><metadata><email>bidyut@viblio.com</email><contactno>408-728-8130</contactno></metadata></user>'
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
def login(session_info, uid):
    url = iv_config.iv_host + 'user/login'
    # Auto-generate password as SHA1 for uid
    sha_instance = hashlib.sha1()
    sha_instance.update(uid)
    password = sha_instance.hexdigest()
    headers = generate_headers(session_info)
    login_xml = '<login xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><loginName>' + uid + '</loginName><password>' + password + '</password></login>'
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
    if r.status_code == requests.codes.ok:
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
    print r, r.content
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print str(soup)
    if (soup.result.status):
        status = soup.result.status.string
    if status == 'Success':
        if(soup.result.description):
            if soup.result.description.string == 'File downloading started':
                time.sleep(60)
                r = requests.post(url, data=analyze_xml, headers=headers)
                if r.status_code == requests.codes.ok:
                    soup = BeautifulSoup(r.content, 'lxml')
                    print str(soup)
        if (soup.result.fileid):
            file_id = soup.result.fileid.string
        if(soup.result.expectedwaitseconds):
            wait_time = int(soup.result.expectedwaitseconds.text)
            return ({'file_id': file_id, 'wait_time': wait_time})
    elif status == 'Failure':
        print 'Got Failure'
        if(soup.result.description):
            description = soup.result.description.string
            print 'description is: ' + description
        if description == 'FR could not process specified file':
            print 'TRYING AGAIN'
            analyze(session_info, user_id, media_url)
        elif description == 'Request failed':
            print 'START OVER'
        elif description == 'Previous file is in process':
            print 'TRYING AGAIN'
            analyze(session_info, user_id, media_url)
        elif description == 'Downloading failed':
            print 'CANNOT DOWNLOAD, EXIT'
        return(soup)
    else: 
        print 'Failed: ' + str(soup)
        return(soup)
## <html><body><result><status>Success</status><fileid>4</fileid><expectedwaitseconds>69</expectedwaitseconds></result></body></html>

## Retrieve Faces API
def retrieve(session_info, user_id, file_id, uuid):
    url = iv_config.iv_host + 'user/' + user_id + '/retrieveFaces?fileID=' + file_id
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print str(soup)
        if (soup.result.status.string == 'Success') & (soup.result.description.string != 'No Results'):
            tracks = soup.result.tracks
            return(tracks)
        else: return(soup)
    else: return(r.content)
# <Result><Status>Success</Status><ExpectedWaitSeconds>0</ExpectedWaitSeconds><Description>No Results</Description></Result>

## Add Person API
def add_person(session_info, user_id):
    name_uuid = str(uuid.uuid4())
    url = iv_config.iv_host + 'user/' + user_id + '/addPerson'
    add_person_xml = '<personDetails xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><firstName>' + name_uuid + '</firstName><lastName>' + name_uuid + '</lastName><description>Friend</description></personDetails>'
    # add_person_xml = '<personDetails><firstName>' + name_uuid + '</firstName><lastName>' + name_uuid + '</lastName><description>Friend</description></personDetails>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=add_person_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print str(soup)
        if str(soup.body.person.status.string) == 'Success':
            person_id = soup.body.person.id.string
            return(person_id)
        else:
            print 'ERROR'
            return(soup)
# <html><body><person><status>Success</status><id>3</id></person></body></html>

def delete_person(session_info, user_id, person_id):
    url = iv_config.iv_host + 'user/' + user_id + '/deletePerson/' + person_id
    headers = generate_headers(session_info)
    r = requests.delete(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        print str(soup)
        if str(soup.body.result.status.string) == 'Success':
            print 'Success'
        else:
            print "Error"
    else: print r.content
#'<?xml version="1.0"?>\r\n<Person><Status>Success</Status><Id>0</Id></Person>\r\n'
def train_person(session_info, user_id, person_id, track_id, file_id, media_url):
    url = iv_config.iv_host + 'user/' + user_id + '/trainPerson?personID=' + person_id + '&trackID=' + track_id + '&fileID=' + file_id
    analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + user_id + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=analyze_xml, headers=headers)
    if r.status_code == requests.codes.OK:
        soup = BeautifulSoup(r.content, 'lxml')
        print soup
        if str(soup.result.status.text) == 'Success':
            return('Success' + str(r.content))

