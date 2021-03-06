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
  <title>Merge Track Faces</title>
 </head>
 <body>

 <p>For each group below, select one of the three or four provided options.</p>
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

def _get_question_html_for_track( track, max_faces ):
    face_count = len( track['faces'] )
    
    html = ""

    track_id = track['track_id']

    if face_count: 
        html = '<tr>'
        html += '<td rowspan="5" style="border-bottom: 1px solid #000;">Group %d</td>' % ( track_id )

        server = config.ImageServer

        for i in range( face_count ):
            face = track['faces'][i]

            html += '<td rowspan="5" style="border-bottom: 1px solid #000;"><img src="%s%s" height="130" width="130" alt="Img. %s" /></td>' % ( server, face['s3_key'] , i )


        for i in range( face_count, max_faces ):
            html += '<td rowspan="5" style="border-bottom: 1px solid #000;"></td>'

        html += '<td><input type="radio" name="answer_%d" value="%d_notface" /></td>' % ( track_id, track_id )
        html += '<td>1. One of the images for Group %d is not a face</td>' % track_id

        html += "</tr>"

        html += '<tr>'
        html += '<td><input type="radio" name="answer_%d" value="%d_badface" /></td>' % ( track_id, track_id )
        html += '<td>2. One of the images for Group %d is unrecognizable, very blurry, or deformed</td>' % track_id
        html += '</tr>'

        html += '<tr>'
        html += '<td><input type="radio" name="answer_%d" value="%d_twoface" /></td>' % ( track_id, track_id )
        html += '<td>3. The faces for Group %d include two or more different people</td>' % track_id
        html += '</tr>'

        html += '<tr>'
        html += '<td><input type="radio" name="answer_%d" value="%d_new" /></td>' % ( track_id, track_id )
        html += '<td>4. Ignoring any groups that had non-faces, or multiple different people, this is the lowest numbered Group that the pictured person appears in.</td>'
        html += '</tr>'

        html += '<tr>'
        if track_id == 0:
            html += '<td style="border-bottom: 1px solid #000;"></td><td style="border-bottom: 1px solid #000;"></td>'
        else:
            html += '<td style="border-bottom: 1px solid #000;"><input type="number" name="merge_%d" min="0" max="%d" step="1" style="width:30px;" /></td>' % ( track_id, track_id - 1 )
            html += '<td style="border-bottom: 1px solid #000;">5. If none of the above were true, enter the lowest numbered Group that also has this person to the left (Ignore any groups that had non-faces, or multiple different people)</td>'
        html += '</tr>'

    return html

def get_question( tracks ):
    '''We rely on the tracks being ordered by increasing track_id to
    constrain the valid selections on group_id, so this sorts the
    input by track_id'''

    html = html_front
    html += form_front
    max_faces = 0

    # Sort the tracks by increasing track_id
    tracks.sort( key = lambda x : x['track_id'] )

    for track in tracks:
        if max_faces < len( track['faces'] ):
            max_faces = len( track['faces'] )
        
    html += '<table style="border-collapse: collapse;">'
    for track in tracks:
        html += _get_question_html_for_track( track, max_faces )
    html += '</table>'
    html += form_back
    html += html_back % ( 220*len( tracks ) + 163 ) 
    
    return html

