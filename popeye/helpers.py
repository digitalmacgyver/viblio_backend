import json
import os

def exif( media_file ):
    basename, ext = os.path.splitext( media_file )
    dirname = os.path.dirname( media_file )
    exif_file = os.path.join( dirname, basename + '_exif.json' )
   
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

        
