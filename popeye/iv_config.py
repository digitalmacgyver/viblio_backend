import pytz

# Parameters provided my IntelliVision
iv_host = 'http://71.6.45.227/FDFRRstService/RestService.svc/'
partner_id = 'VIBLIO'
local_id = '9876543210'
api_key = 'AAA111BBB222'
xmlns = {'xmlns': 'http://schemas.datacontract.org/2004/07/RESTFulDemo'}
# Parameters used iv.py
time_zone = pytz.timezone("GMT")
minimum_detection_score = 5
minimum_recognition_score = 60
# Default uid for testing
uid = 'C209A678-03AF-11E3-8D79-41BD85EDDE05'
