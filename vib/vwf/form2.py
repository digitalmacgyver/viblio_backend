#!/usr/bin/env python

# Create hello world HIT.

from vib.thirdParty.mturkcore import MechanicalTurk

mt = MechanicalTurk( 
    { 
        'use_sandbox'           : True, 
        'stdout_log'            : True, 
        'aws_key'     : 'AKIAJHD46VMHB2FBEMMA',
        'aws_secret_key' : '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',
        } 
    )


MergeHITTypeId = '2PCIA0RYNJ96UXSXBA2MMTUHYKA837'

media_uuid = '123456'

create_options = {
    # DEBUG - get this from configuration
    'HITTypeId' : MergeHITTypeId,
    'LifetimeInSeconds' : 36*60*60,
    'RequesterAnnotation' : media_uuid,
    'UniqueRequestToken' : 'merge-' + media_uuid,
    'Question' : 
    '''
'''
    }

result = mt.create_request( 'CreateHIT', create_options )
print "Result was %s" % result

hit_id = None
try:
    hit_id = result['CreateHITResponse']['HIT']['HITId']
except:
    # Handle the case where this hit already exists.
    hit_id = result['CreateHITResponse']['HIT']['Request']['Errors']['Error']['Data'][1]['Value']

get_options = {
    'HITId' : hit_id
    }

result = mt.create_request( 'GetHIT', get_options )
print "Result was %s" % result

get_assignments_options = {
    'HITId' : hit_id
    }

def _get_track_html( track ):
    return '''
  <table>
    <tr>
      <td><img src="http://web.cacs.louisiana.edu/~cice/mesh/mary.jpg" height="50" width="50" /></td>
      <td><img src="http://imalbum.aufeminin.com/album/D20130702/hairstyles-for-oval-shaped-faces1-921202_H165451_S.jpg" height="50" width="50" /></td>
      <td><img src="https://si0.twimg.com/profile_images/3528477267/a5d136b09d331805e88d24f69c0d0fdb.jpeg" height="50" width="50" /></td>
      <td><img src="http://31.media.tumblr.com/avatar_8f99bee205d9_64.png" height="50" width="50" /></td>
      <td><img src="http://imalbum.aufeminin.com/album/D20130621/919480_YATQJ5UWKKEBPFBMUSOT8XOYQYADGF_hairstyles-for-square-faces1_H000444_S.jpg" height="50" width="50" /></td>
    </tr>
  </table>
'''


form_front = '''
  <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
'''

def _get_form_html( tracks ):
    return '''  
    <p>Select the first true statement below:</p>


    <table border="1px">
      <tr>
        <td><input type="radio" name="answer" value="not_face" /></td>
        <td>One of the above images is not a face</td>
      </tr>  
      <tr>
        <td><input type="radio" name="answer" value="two_face" /></td>
        <td>The face images above are of two or more different people.</td>
      </tr>  
      <tr>
        <td><input type="radio" name="answer" value="recognized_face" /></td>
        <td>The images above are of this person:<img src="https://si0.twimg.com/profile_images/378800000060141540/c140d338c308894eb0475045010aeeb5.jpeg" height="50" width="50"/></td>
      </tr>  
      <tr>
        <td></td>
        <td>If the images above are of one of the people below, click the button under the person:</td>
      <tr>
      <tr>
        <td></td>
        <td>
        <table>
          <tr>
            <td><img src="https://si0.twimg.com/profile_images/378800000598797835/996bbcad7ddf2277bd5352dcf165671a_normal.jpeg" height="50" width="50"/></td>
            <td><img src="http://imalbum.aufeminin.com/album/D20130614/hairstyles-for-heartshaped-faces1-918395_H125134_S.jpg" height="50" width="50"/></td>
            <td><img src="https://si0.twimg.com/profile_images/3312497315/4132de7875e8184ff04b432b40fc012f_normal.jpeg" height="50" width="50"/></td>
            <td><img src="https://lh6.googleusercontent.com/-6tvTjoGnBCI/AAAAAAAAAAI/AAAAAAAAAAA/rO4GhBZXLT8/s48-c-k/photo.jpg" height="50" width="50"/></td>
            <td><img src="http://www.cs.indiana.edu/~kinzler/images/kinzler_icon.gif" height="50" width="50"/></td>
            <td><img src="http://web.cacs.louisiana.edu/~cice/mesh/jane.jpg" height="50" width="50"/></td>
            <td><img src="http://s4.evcdn.com/images/block/I0-001/013/818/515-1.jpeg_/many-faces-hildegard-bingen-new-doctor-church-15.jpeg" height="50" width="50"/></td>
            <td><img src="https://lh5.googleusercontent.com/-jCBTc4m12gE/AAAAAAAAAAI/AAAAAAAAAAA/htwrLaSvByU/s48-c-k/photo.jpg" height="50" width="50"/></td>
            <td><img src="http://imalbum.aufeminin.com/album/D20130705/922708_DFNPE5EYHLZB38PGXSXI3Y1J5IDW3H_hairstyles-for-long-face-shape2_H023948_S.jpg" height="50" width="50"/></td>
            <td><img src="https://moodle.org/pluginfile.php/56521/user/icon/moodleofficial/f2?rev=438779" height="50" width="50"/></td>
          </tr>
          <tr>
            <td><input type="radio" name="answer" value="face_001" /></td>
            <td><input type="radio" name="answer" value="face_002" /></td>
            <td><input type="radio" name="answer" value="face_003" /></td>
            <td><input type="radio" name="answer" value="face_004" /></td>
            <td><input type="radio" name="answer" value="face_005" /></td>
            <td><input type="radio" name="answer" value="face_006" /></td>
            <td><input type="radio" name="answer" value="face_007" /></td>
            <td><input type="radio" name="answer" value="face_008" /></td>
            <td><input type="radio" name="answer" value="face_009" /></td>
            <td><input type="radio" name="answer" value="face_010" /></td>
          </tr>
        </table>
        </td>
      </tr>  
      <tr>
        <td><input type="radio" name="answer" value="new_face" /></td>
        <td>None of the above were true</td>
      </tr>  
    </table>
  <input type='hidden' value='' name='assignmentId' id='assignmentId'/>
  <p><input type='submit' id='submitButton' value='Submit' /></p>
  </form>
'''

html_back = '''
  <script language='Javascript'>turkSetAssignmentID();</script>
 </body>
</html>
]]>
  </HTMLContent>
  <FrameHeight>600</FrameHeight>
</HTMLQuestion>
'''

html_front = 
'''
<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
  <HTMLContent><![CDATA[
<!DOCTYPE html>
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
  <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
 </head>
 <body>

  <p>
  For the face images below:
  </p>
'''


