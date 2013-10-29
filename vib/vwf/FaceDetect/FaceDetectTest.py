from vib.vwf.FaceDetect.Detect import Detect

media_uuid = '36cf0d30-3494-11e3-8d11-3da8fd0aefbe'
user_uuid = 'C209A678-03AF-11E3-8D79-41BD85EDDE05'
s3_bucket = 'viblio-uploaded-files'

options = {'media_uuid': media_uuid, 'user_uuid': user_uuid, 's3_bucket': s3_bucket}
face_detector = Detect()
tracks = face_detector.run_task(options)
