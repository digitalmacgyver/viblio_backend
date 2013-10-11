from bs4 import BeautifulSoup, Tag
import datetime
import hashlib
import logging
import requests
import sys
import time
import threading
import uuid
import json
import iv_config

def get_log():
    return logging.getLogger( 'popeye.' + str( threading.current_thread().name ) )

def open_session():
    log = get_log()

    #Generate session.xml for IntelliVision
    tag = Tag( name = "session")
    tag.attrs = iv_config.xmlns
    partnerId_tag = Tag( name='partnerId')
    partnerId_tag.string = iv_config.partner_id
    apiKey_tag = Tag(name='apiKey')
    apiKey_tag.string = iv_config.api_key
    localId_tag = Tag(name='localId')
    localId_tag.string = iv_config.local_id
    tag.insert(0, localId_tag)
    tag.insert(0, apiKey_tag)
    tag.insert(0, partnerId_tag)
    session_xml = str(tag)
    # session_xml = '<?xml version="1.0"?><session xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><partnerId>VIBLIO</partnerId><apiKey>AAA111BBB222</apiKey><localId>9876543210</localId></session>'
    url = iv_config.iv_host + 'session'
    raw_date = datetime.datetime.now(iv_config.time_zone)
    formatted_date = raw_date.strftime('%a, %d %b %Y %H:%M:%S %Z')  
    headers = {'Content-Type':'text/xml', 'Date':formatted_date}
    r = requests.post(url, data=session_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        log.info( str(soup) )
        try:
            session_key = soup.result.sessionkey.string
            session_secret = soup.result.sessionsecret.string
            session_info = {'key': session_key, 
                            'secret': session_secret}
            return(session_info)
        except:
            log.error( 'Failed to extract session info' )
            return ('False')

## compute hashed values for subsequent API calls
def generate_headers(session_info ):
    log = get_log()

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
def close_session(session_info ):
    log = get_log()

    url = iv_config.iv_host + 'endSession'
    headers = generate_headers(session_info)
    r = requests.delete(url, headers=headers)
    if r.status_code == requests.codes.ok:
        log.info( 'session closed' + r.content )
    else:
        log.error( "error" + r.content )

## Register User API
def register_user(session_info, uid ):
    log = get_log()

    url = iv_config.iv_host + 'user'
    sha_instance = hashlib.sha1()
    sha_instance.update(uid)
    password = sha_instance.hexdigest()
    # Generate register.xml for IntelliVision
    tag = Tag( name = "user")
    tag.attrs = iv_config.xmlns
    name_tag = Tag( name='name')
    name_tag.string = uid
    loginName_tag = Tag(name='loginName')
    loginName_tag.string = uid
    password_tag = Tag(name='password')
    password_tag.string = password
    metadata_tag = Tag(name='metadata')
    metadata_tag.string = ''
    email_tag = Tag(name='email')
    email_tag.string = 'user@viblio.com'
    contactno_tag = Tag(name='contactno')
    contactno_tag.string = '408-922-9800'
    tag.insert(0, metadata_tag)
    tag.metadata.insert(0, contactno_tag)
    tag.metadata.insert(0, email_tag)
    tag.insert(0, password_tag)
    tag.insert(0, loginName_tag)
    tag.insert(0, name_tag)
    register_xml = str(tag)
    # register_xml = '<user xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><name>' + uid + '</name><loginName>' + uid + '</loginName><password>' + password + '</password><metadata><email>bidyut@viblio.com</email><contactno>408-728-8130</contactno></metadata></user>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=register_xml, headers=headers)
    log.info( r.content )
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if soup.status.string == 'Success':
            log.info( "User registered successfully " + uid )
            return
        else:
            log.error( "Error: " + r.content )

## Login API
def login(session_info, uid ):
    log = get_log()

    url = iv_config.iv_host + 'user/login'
    # Auto-generate password as SHA1 for uid
    sha_instance = hashlib.sha1()
    sha_instance.update(uid)
    password = sha_instance.hexdigest()
    #Generate login.xml for IntelliVision
    tag = Tag( name = "login")
    tag.attrs = iv_config.xmlns
    loginName_tag = Tag( name='loginName')
    loginName_tag.string = uid
    password_tag = Tag(name='password')
    password_tag.string = password
    tag.insert(0, password_tag)
    tag.insert(0, loginName_tag)
    login_xml = str(tag)
    # login_xml = '<login xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><loginName>' + uid + '</loginName><password>' + password + '</password></login>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=login_xml, headers=headers)
    log.info( r.content )
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if soup.status.string == 'Success':
            user_id = soup.id.string
            return user_id
        # if soup.description.string == 'User is not registered':
        elif soup.status.string == 'Failure':
            register_user(session_info, uid)
            user_id = login(session_info, uid)
            return user_id
        else:
            log.error( "Error: " + r.content )

## Get User Details API
def get_user_details(session_info, user_id ):
    log = get_log()

    url = iv_config.iv_host + 'user/' + user_id + '/getUser'
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
                user_id = str(soup.id.text)
                log.info( user_id )
                return (user_id)
        else:
            log.error( "Error: " + r.content )

## Logout user API
def logout(session_info, user_id ):
    log = get_log()

    url = iv_config.iv_host + 'user/' + user_id + '/logout'
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        if (str(soup.status.text) == 'Success'):
            log.info( r.content )
            return (user_id)
        else:
            log.error( "Error: " + r.content )

## Analyze face API
def analyze(session_info, user_id, uid, media_url ):
    log = get_log()

    # create analyze.xml for IntelliVision
    tag = Tag( name = "data")
    tag.attrs = iv_config.xmlns
    user_id_tag = Tag( name='userid')
    user_id_tag.string = user_id
    media_url_tag = Tag(name='mediaURL')
    media_url_tag.string = media_url
    recognize_tag = Tag(name = "recognize")
    recognize_tag.string = '01'
    tag.insert(0, recognize_tag)
    tag.insert(0, media_url_tag)
    tag.insert(0, user_id_tag)
    analyze_xml = str(tag)
    url = iv_config.iv_host + 'user/' + user_id + '/analyzeFaces'
    headers = generate_headers(session_info)
    for trial in range (1, 20):
        log.info( "Trial number: " + str(trial) )
        r = requests.post(url, data=analyze_xml, headers=headers)
        if r.status_code == requests.codes.ok:
            soup = BeautifulSoup(r.content, 'lxml')
            log.info( str(soup) )
            if (soup.result.status):
                status = soup.result.status.string
                if status == 'Success':
                    if(soup.result.description):
                        if soup.result.description.string == 'File downloading started':
                            log.info( 'Sleeping for: 60 seconds' )
                            time.sleep(60)
                            r = requests.post(url, data=analyze_xml, headers=headers)
                            if r.status_code == requests.codes.ok:
                                soup = BeautifulSoup(r.content, 'lxml')
                                log.info( str(soup) )
                    elif (soup.result.fileid):
                        file_id = soup.result.fileid.string
                        if(soup.result.expectedwaitseconds):
                            wait_time = int(soup.result.expectedwaitseconds.text)
                            return ({'file_id': file_id, 
                                     'wait_time': wait_time, 
                                     'key': session_info['key'], 
                                     'secret': session_info['secret'],
                                     'user_id': user_id})
                        return ({'file_id': file_id,
                                 'key': session_info['key'], 
                                 'secret': session_info['secret'],
                                 'user_id': user_id})
                    else:
                        log.info( 'Unknown success case' )
                        log.info( str(soup) )
                elif status == 'Failure':
                    if(soup.result.description):
                        description = soup.result.description.string
                        log.info( 'description is: ' + description )
                        if description == 'FR could not process specified file':
                            log.info( 'TRYING AGAIN due to FR' )
                        elif description == 'Failed to fetch data':
                            log.info( 'TRYING AGAIN as Failed to fetch data' )
                        elif description == 'Previous file is in process.':
                            log.info( 'TRYING AGAIN as previous file is in progress, sleep for 30 seconds' )
                            time.sleep(30)
                        elif description == 'Previous file downloading is in progress':
                            log.info( 'TRYING AGAIN as previous file is in progress, sleep for 30 seconds' )
                            time.sleep(30)
                        elif description == 'Request failed':
                            log.info( 'START OVER close the session and restart' )
                            session_info = open_session()
                            user_id = login(session_info, uid)
                        elif description == 'Downloading failed':
                            log.info( 'CANNOT DOWNLOAD, EXIT' )
                            return ('__ANALYSIS__FAILED__')
                        else:
                            log.warning( 'Unknown failure case' )
                            log.warning( str(soup) )
                    else:
                        log.error( 'Encountered an error in getting the description' )
                        log.error( str(soup) )
                        return ('__ANALYSIS__FAILED__')
                else :
                    log.error( ' gk gk gk step 4.1.1 ELSE' )
                    log.error( ' soup was ' )
                    log.error( str( soup ) )
                    return ('__ANALYSIS__FAILED__')
            else:
                log.info( ' gk gk gk step 4.1  --> else' )
        time.sleep(5)

## Retrieve Faces API
def retrieve(session_info, user_id, file_id ):
    log = get_log()

    url = iv_config.iv_host + 'user/' + user_id + '/retrieveFaces?fileID=' + file_id
    headers = generate_headers(session_info)
    r = requests.get(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        log.info( str(soup) )
        if (soup.result.status.string == 'Success'):
            log.info( 'success' )
            if(soup.find('description')):
                log.info( ' found description' )
                if (soup.description.string == 'No Results'):
                    log.info( 'No Tracks Found' )
                    return ('No Tracks')
            else:
                tracks = soup.result.tracks
                return(tracks)
        else: return(soup)
    else: return(r.content)
# <Result><Status>Success</Status><ExpectedWaitSeconds>0</ExpectedWaitSeconds><Description>No Results</Description></Result>
# <html><body><result><status>Success</status><expectedwaitseconds>0</expectedwaitseconds><tracks><numberoftracks>5</numberoftracks><track><trackid>0</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam21_24-09-2013_06-10-34-497_0.jpg</bestfaceframe><starttime>2013-09-24 06:10:34</starttime><endtime>2013-09-24 06:10:35</endtime><width>110</width><height>110</height><facecenterx>910</facecenterx><facecentery>958</facecentery><detectionscore>12</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track><track><trackid>1</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam21_24-09-2013_06-11-22-217_1.jpg</bestfaceframe><starttime>2013-09-24 06:11:22</starttime><endtime>2013-09-24 06:11:22</endtime><width>254</width><height>254</height><facecenterx>969</facecenterx><facecentery>249</facecentery><detectionscore>4</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track><track><trackid>2</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam21_24-09-2013_06-11-46-188_2.jpg</bestfaceframe><starttime>2013-09-24 06:11:46</starttime><endtime>2013-09-24 06:11:46</endtime><width>102</width><height>102</height><facecenterx>252</facecenterx><facecentery>614</facecentery><detectionscore>5</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track><track><trackid>3</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam21_24-09-2013_06-11-51-220_3.jpg</bestfaceframe><starttime>2013-09-24 06:11:51</starttime><endtime>2013-09-24 06:11:51</endtime><width>110</width><height>110</height><facecenterx>257</facecenterx><facecentery>608</facecentery><detectionscore>4</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track><track><trackid>4</trackid><personid>-1</personid><bestfaceframe>http://71.6.45.228/FDFRRstService/Detected/FACES/FDFR_Cam21_24-09-2013_06-11-51-220_4.jpg</bestfaceframe><starttime>2013-09-24 06:11:51</starttime><endtime>2013-09-24 06:11:51</endtime><width>257</width><height>257</height><facecenterx>1394</facecenterx><facecentery>192</facecentery><detectionscore>29</detectionscore><recognitionconfidence>0.00</recognitionconfidence></track></tracks></result></body></html>

## Add Person API
def add_person(session_info, user_id ):
    log = get_log()

    name_uuid = str(uuid.uuid4())
    url = iv_config.iv_host + 'user/' + user_id + '/addPerson'
    add_person_xml = '<personDetails xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><firstName>' + name_uuid + '</firstName><lastName>' + name_uuid + '</lastName><description>Friend</description></personDetails>'
    # add_person_xml = '<personDetails><firstName>' + name_uuid + '</firstName><lastName>' + name_uuid + '</lastName><description>Friend</description></personDetails>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=add_person_xml, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        log.info( str(soup) )
        if str(soup.body.person.status.string) == 'Success':
            person_id = soup.body.person.id.string
            return(person_id)
        else:
            log.error( 'ERROR' )
            return(soup)
# <html><body><person><status>Success</status><id>3</id></person></bodsession_info = iv.open_session()y></html>

def delete_person(session_info, user_id, person_id ):
    log = get_log()

    url = iv_config.iv_host + 'user/' + user_id + '/deletePerson/' + person_id
    headers = generate_headers(session_info)
    r = requests.delete(url, headers=headers)
    if r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.content, 'lxml')
        log.info( str(soup) )
        if str(soup.body.result.status.string) == 'Success':
            log.info( 'Success' )
        else:
            log.error( "Error" )
    else: log.info( r.content )
#'<?xml version="1.0"?>\r\n<Person><Status>Success</Status><Id>0</Id></Person>\r\n'


def train_person(session_info, user_id, person_id, track_id, file_id, media_url):
    log = get_log()

    log.info( 'Training for user_id: %s, person_id: %s, track_id: %s, file_id: %s, and media_url: %s' % ( user_id, person_id, track_id, file_id, media_url ) )

    url = iv_config.iv_host + 'user/' + user_id + '/trainPerson?personID=' + person_id + '&trackID=' + track_id + '&fileID=' + file_id
    analyze_xml = '<data xmlns="http://schemas.datacontract.org/2004/07/RESTFulDemo"><userId>' + user_id + '</userId><mediaURL>' + media_url + '</mediaURL><recognize>01</recognize></data>'
    headers = generate_headers(session_info)
    r = requests.post(url, data=analyze_xml, headers=headers)
    log.info( r.content )
    if r.status_code == requests.codes.OK:
        soup = BeautifulSoup(r.content, 'lxml')
        log.info( str( soup ) )
        if str(soup.result.status.text) == 'Success':
            return('Success')
        else:
            return('Failure')

def get_tracks(session_info, user_id, uid, media_url):
    log = get_log()
    response = analyze(session_info, user_id, uid, media_url)
    session_info = {'key': response['key'], 
                    'secret': response['secret']}
    user_id = response['user_id']
    file_id = response['file_id']
    # in case wait_time is absent, wait for fixed time
    if response.get( 'wait_time' ):
        wait_time = response['wait_time']
        time.sleep(wait_time)
    else:
        log.info(log, 'waiting for 120 seconds')
        time.sleep(120)
    tracks = retrieve(session_info, user_id, file_id)
    if tracks == 'No Tracks':
        log.info (log, 'No tracks found')
        return json.dumps( {"tracks": {"file_id": file_id, "numberoftracks": "0"}} )
    for i,track in enumerate(tracks.findAll('track')):
        track_id = track.trackid.string
        person_id = track.personid.string
        detection_score = float(track.detectionscore.string)
        if ( person_id == '-1' ) & ( detection_score > iv_config.minimum_detection_score ):
            # Train unknown person if detection score is high enough
            new_person_id = add_person(session_info, user_id)
            log.info( 'Added a new person: ' + new_person_id )
            try:
                log.info( 'training: ' + new_person_id )
                result = train_person(session_info, user_id, new_person_id, track_id, file_id, media_url)
                if result == 'Success':
                    get_tracks(session_info, user_id, uid, media_url)
                else:
                    delete_person(session_info, user_id, new_person_id)
            except:
                log.warning( 'Failed to train unknown person' )
        else:
            # Known person or Unknown person with low detection score
            print 'Known person or Unknown person with low detection score'
    return (tracks)
