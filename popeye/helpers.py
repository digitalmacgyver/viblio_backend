import json
import os

def exif( filenames ):
    media_file = filenames['video']['input']
    exif_file = filenames['exif']['output']
   
    try:
        command = '/usr/bin/exiftool -j -w! _exif.json -c %+.6f ' + media_file
        os.system( command )
    except Exception, e:
        print 'EXIF extraction failed, error was: %s' % ( e )
        raise

    file_handle = open( exif_file )

    info = json.load( file_handle )

    exif_data = {}
    if info[0]:
        exif_data = info[0]

    file_ext     = str( exif_data.get( 'FileType', '' ) )
    mime_type    = str( exif_data.get( 'MIMEType', '' ) )
    lat          = str( exif_data.get( 'GPSLatitude', '' ) )
    lng          = str( exif_data.get( 'GPSLongitude', '' ) )
    rotation     = str( exif_data.get( 'Rotation', '0' ) )
    frame_rate   = str( exif_data.get( 'VideoFrameRate', '24' ) )
    create_date  = str( exif_data.get( 'MediaCreateDate', '' ) )

    return( { 'file_ext'    : file_ext, 
              'mime_type'   : mime_type, 
              'lat'         : lat, 
              'lng'         : lng, 
              'create_date' : create_date, 
              'rotation'    : rotation, 
              'frame_rate'  : frame_rate
              } )

def lc_extension( basename, ext ):
    '''Lowercase the extension of our input file, and rename the file
    to match.'''

    lc_ext = ext.lower()
    if lc_ext != ext:
        os.rename( basename + ext, basename + lc_ext )

    return basename, lc_ext

def get_faces(avi_video):
    basename, ext = os.path.splitext( avi_video )
    media_uuid = os.path.split( basename )[1]
    media_url = 'http://s3-us-west-2.amazonaws.com/viblio-uploaded-files/' + media_uuid + '/' + media_uuid + ext
    print media_url
    print basename
    session_info = iv.open_session()
    user_id = iv.login(session_info, iv_config.uid)
    file_id = iv.analyze(session_info, user_id, media_url)
    print file_id
    x = iv.retrieve(session_info, user_id, file_id, basename)
    iv.logout(session_info, user_id)
    iv.close_session(session_info)
    return (x)

def create_filenames (full_filename):
    # Basename includes the absolute path and everything up to the extension.
    basename, ext = os.path.splitext( full_filename )
    # Rename the file so its extension is in lower case.
    basename, ext = lc_extension( basename, ext )
    # By convention the filename is the media_uuid.
    media_uuid = os.path.split( basename )[1]
    input_video = full_filename
    input_info = basename + '.json'
    input_metadata = basename + '_metadata.json'
    # Output file names
    output_video = basename + '.mp4'
    avi_video = basename + '.avi'
    output_thumbnail = basename + '_thumbnail.jpg'
    output_poster = basename + '_poster.jpg'
    output_metadata = input_metadata
    output_face = basename + '_face0.jpg'
    output_exif = basename + '_exif.json'
    
    video_key = media_uuid + '/' + os.path.basename( output_video )
    avi_key = media_uuid + '/' + os.path.basename( avi_video )
    thumbnail_key = media_uuid + '/' + os.path.basename( output_thumbnail )
    poster_key = media_uuid + '/' + os.path.basename( output_poster )
    metadata_key = media_uuid + '/' + os.path.basename( output_metadata )
    face_key = media_uuid + '/' + os.path.basename( output_face )
    exif_key = media_uuid + '/' + os.path.basename( output_exif )
    filenames = {
        'uuid': media_uuid,
        'info': input_info,
        'video_key': video_key,
        'avi_key': avi_key,
        'thumbnail_key': thumbnail_key,
        'poster_key': poster_key,
        'metadata_key': metadata_key,
        'face_key': face_key,
        'exif_key': exif_key,
        'video': {
            'input': input_video,
            'output': output_video,
            'avi': avi_video
            },
        'thumbnail': {
            'input': output_video,
            'output': output_thumbnail
            },
        'poster': {
            'input': output_video,
            'output': output_poster
            },
        'metadata': {
            'input': input_metadata,
            'output': output_metadata
            },
        'face': {
            'input': output_video,
            'output': output_face
            },
        'exif': {
            'output': output_exif
            }
        }
    return(filenames)        
