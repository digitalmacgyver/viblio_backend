#!/usr/bin/env python

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

form_front = '''
  <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
'''

form_back = '''
  <input type='hidden' value='' name='assignmentId' id='assignmentId'/>
  <p><input type='submit' id='submitButton' value='Submit' /></p>
  </form>
'''

html_front = '''<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
  <HTMLContent><![CDATA[
<!DOCTYPE html>
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
  <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
  <title>Recognize Faces</title>
 </head>
 <body>

 <p>For the person pictured below, select one answer:</p>
'''

html_back = '''
  <script language='Javascript'>turkSetAssignmentID();</script>
 </body>
</html>
]]>
  </HTMLContent>
  <FrameHeight>%d</FrameHeight>
</HTMLQuestion>
'''

def _get_contact_row_html( contacts, start_idx, cell_count ):

    server = config.ImageServer

    contact_count = len( contacts )

    html = "<tr>"
    for i in range( contact_count ):
        contact_uuid, contact = contacts[i]
        
        html += '<td><img src="%s%s" height="50" width="50" alt="Img. %s" /></td>' % ( server, contact['picture_uri'], start_idx + i )

    for i in range( contact_count, cell_count ):
        html += '<td></td>'

    html += '</tr>'
    html += '<tr>'

    for i in range( contact_count ):
        contact_uuid, contact = contacts[i]
        
        html += '<td><input type="radio" name="answer" value="recognized_%s" /></td>' % ( contact_uuid )

    for i in range( contact_count, cell_count ):
        html += '<td></td>'

    html += '</tr>'

    return html

def get_question( person_tracks, contacts, guess ):
    html = html_front

    server = config.ImageServer
    
    # Create a table of the person we're recognizing
    html += '<table><tr>'
    for face in person_tracks[0]['faces']:
        html += '<td><img src="%s%s" height="50" width="50" alt="An Image" /></td>' % ( server, face['s3_key'] )
    html += '</tr></table>'
   
    html += form_front

    html += '<table border="1">'

    if guess:
        html += '<tr>'
        html += '<td><input type="radio" name="answer" value="recognized_%s" /></td>' % ( guess['uuid'] )
        html += '<td>The person  is the same as this person: <img src="%s%s" height="50" width="50" alt="Img. %s" /></td>' % ( server, guess['picture_uri'], 'guess' )
        html += '</tr>'

    html += '<tr>'
    html += '<td></td>'
    html += '<td>The person is one of these people:</td>'
    html += '</tr>'

    html += '<tr>'
    html += '<td></td>'
    html += '<td>'

    html += '<table>'
    col_faces = 12

    for idx in range( 0, len( contacts ), col_faces ):
        html += _get_contact_row_html( contacts[idx:idx+col_faces], idx, col_faces )
        
    html += '</table>'

    html += '</td>'
    html += '</tr>'

    html += '<tr>'
    html += '<td><input type="radio" name="answer" value="new_face" /></td>'
    html += '<td>The person was none of the above people.</td>'
    html += '</tr>'
    
    html += '</table>'
    html += form_back
    # Parenthesis because of integer division not being associative.
    html += html_back % ( 85*( 1+len( contacts )/col_faces ) + 325 ) 
    
    return html

