#!/usr/bin/env python

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
        html += '<td rowspan="4" style="border-bottom: 1px solid #000;">Group %d</td>' % ( track_id )

        for i in range( face_count ):
            face = track['faces'][i]
            server = "http://staging.viblio.com/s/ip/"
            if face['s3_bucket'] != "viblio-uploaded-files":
                server = "http://prod.viblio.com/s/ip/"

            html += '<td rowspan="4" style="border-bottom: 1px solid #000;"><img src="%s%s" height="50" width="50" alt="Img. %s" /></td>' % ( server, face['s3_key'] , i )


        for i in range( face_count, max_faces ):
            html += '<td rowspan="4" style="border-bottom: 1px solid #000;"></td>'

        html += '<td><input type="radio" name="answer_%d" value="%d_notface" /></td>' % ( track_id, track_id )
        html += '<td>1. One of the images for Group %d is not a face</td>' % track_id

        html += "</tr>"

        html += '<tr>'
        html += '<td><input type="radio" name="answer_%d" value="%d_twoface" /></td>' % ( track_id, track_id )
        html += '<td>2. The faces for Group %d include two or more different people</td>' % track_id
        html += '</tr>'

        html += '<tr>'
        html += '<td><input type="radio" name="answer_%d" value="%d_new" /></td>' % ( track_id, track_id )
        html += '<td>3. Ignoring any groups that had non-faces, or multiple different people, this is the lowest numbered Group that the pictured person appears in.</td>'
        html += '</tr>'

        html += '<tr>'
        if track_id == 0:
            html += '<td style="border-bottom: 1px solid #000;"></td><td style="border-bottom: 1px solid #000;"></td>'
        else:
            html += '<td style="border-bottom: 1px solid #000;"><input type="number" name="merge_track_%d" min="0" max="%d" step="1" style="width:30px;" /></td>' % ( track_id, track_id - 1 )
            html += '<td style="border-bottom: 1px solid #000;">4. If none of the above were true, enter the lowest numbered Group that also has this person to the left (Ignore any groups that had non-faces, or multiple differnent people)</td>'
        html += '</tr>'

    return html

def get_question( tracks ):
    html = html_front
    html += form_front
    max_faces = 0

    for track in tracks:
        if max_faces < len( track['faces'] ):
            max_faces = len( track['faces'] )
        
    html += '<table style="border-collapse: collapse;">'
    for track in tracks:
        html += _get_question_html_for_track( track, max_faces )
    html += '</table>'
    html += form_back
    html += html_back % ( 150*len( tracks ) + 100 ) 
    
    return html

#get_assignments_options = {
#    'HITId' : hit_id
#    }

#assignment = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )

#answer = result['GetAssignmentsForHITResponse']['GetAssignmentsForHITResult']['Assignment']['Answer']
#answer = mt.get_response_element( 'Answer', assignment )
#answer_dict = xmltodict.parse( answer )

#for answer in answer_dict['QuestionFormAnswers']['Answer']:
#    label = answer['QuestionIdentifier']
#    value = answer['FreeText']

# NOTE: We'll get back merge_track_n for everything except track 0,
# just with a value of None if it wasn't selected.  Typical output:
# merge_track_1 : None
# merge_track_2 : None
# merge_track_3 : 1
# merge_track_4 : 2
# answer_0 : 0_new
# answer_1 : 1_new
# answer_2 : 2_new

