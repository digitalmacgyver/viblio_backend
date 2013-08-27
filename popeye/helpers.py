import json
import os

def exif (media_file):
    basename, ext = os.path.splitext(media_file)
    dirname = os.path.dirname(media_file)
    exif_file = os.path.join(dirname, basename + '_exif.json')
    
    try:
        command = '/home/viblio/exiftool/exiftool -j -w! _exif.json -c %+.6f ' + media_file
        os.system (command)
    except:
        print 'exif extraction failed'
    file_handle = open(exif_file)
    info = json.load(file_handle)

    if info[0]['FileType']:
        file_ext = str(info[0]['FileType'])
    else: file_ext = ''
    if info[0]['MIMEType']:
        mime_type = str(info[0]['MIMEType'])
    else: mime_type = ''

    if info[0]['GPSLatitude']:
        lat = str(info[0]['GPSLatitude'])
    else: lat= ''
    if info[0]['GPSLongitude']:
        lng = str(info[0]['GPSLongitude'])
    else: lng = ''

    if info[0]['Rotation']:
        rotation = str(info[0]['Rotation'])
    else: rotation = '0'
    if info[0]['VideoFrameRate']:
        frame_rate = str(info[0]['VideoFrameRate'])
    else: frame_rate = '24'
    if info[0]['MediaCreateDate']:
        create_date = str(info[0]['MediaCreateDate'])
    else: create_date = ''

    return({'file_ext': file_ext, 'mime_type': mime_type, 'lat': lat, 'lng': lng, 'create_date': create_date, 'rotation': rotation, 'frame_rate': frame_rate})

