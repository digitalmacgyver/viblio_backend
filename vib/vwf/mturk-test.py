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
<QuestionForm xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd">
  <Overview>
    <Title>Sample Merge Question</Title>
  </Overview>
  <Question>
    <QuestionIdentifier>not_face</QuestionIdentifier>
     <QuestionContent><Text>Question 1</Text></QuestionContent>
     <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>1</MinSelectionCount>
        <MaxSelectionCount>1</MaxSelectionCount>
        <StyleSuggestion>radiobutton</StyleSuggestion>

        <Selections>
          <Selection>
          <SelectionIdentifier>not_face_selection</SelectionIdentifier>
          <Text>Check here if one of the above images is not a face</Text>
          </Selection>

          <Selection>
          <SelectionIdentifier>two_face_selection</SelectionIdentifier>
          <Text>Check here if there are two different people</Text>
          </Selection>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
</QuestionForm>
'''
    }

#result = mt.create_request( 'CreateHIT', create_options )
#print "Result was %s" % result

register_hit_options = {
    'Title' : 'Recognize Face',
    'Description' : 'Given a face, match it against a list of potential matching faces, or decide there is no match.',
    'Reward' : {
        'Amount' : 0.00,
        'CurrencyCode' : 'USD'
        },
    'AssignmentDurationInSeconds' : 3600,
    'Keywords' : 'viblio',
    'AutoApprovalDelayInSeconds' : 0,
    'QualificationRequirement' : {
        'QualificationTypeId' : '2EA1XERSQV6AYZXSTYUHYWAVKM791C',
        'Comparator' : 'Exists',
        'RequiredToPreview' : True#result = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'GetAssignmentsForHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'e966dd16-6639-4be3-894a-ed4da3de6621')])), (u'GetAssignmentsForHITResult', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'NumResults', u'1'), (u'TotalNumResults', u'1'), (u'PageNumber', u'1'), (u'Assignment', OrderedDict([(u'AssignmentId', u'2V12HECWA6X752KNQ53P8KXPUA4LKK'), (u'WorkerId', u'A2UAN9XAD1587R'), (u'HITId', u'2NA8SV7WGKCG2ZTENFU3PHAP1WI1RQ'), (u'AssignmentStatus', u'Submitted'), (u'AutoApprovalTime', u'2013-10-24T08:19:51Z'), (u'AcceptTime', u'2013-10-24T08:09:19Z'), (u'SubmitTime', u'2013-10-24T08:19:51Z'), (u'Answer', u'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<QuestionFormAnswers xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd">\n<Answer>\n<QuestionIdentifier>answer</QuestionIdentifier>\n<FreeText>recognized_face</FreeText>\n</Answer>\n</QuestionFormAnswers>')]))]))]))])

        }
    }

#result = mt.create_request( 'RegisterHITType', register_hit_options )

# DEBUG - Need to use HTML Create Option because otherwise there is no
# way to put all known contacts in a tabular grid.  Also it's a little
# nicer that I can make everything one radio button.

# Looks like I can lay out 12 things wide no problem.
# Height: 600 + 100 for each row in the table.

# DEBUG - I might have a problem with the top Submit button.

html_create_options = {
    'Title' : 'My Test Hit',
    'Description' : 'Lots of details',
    'Question' : 
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

  <table>
    <tr>
      <td><img src="http://web.cacs.louisiana.edu/~cice/mesh/mary.jpg" height="50" width="50" /></td>
      <td><img src="http://imalbum.aufeminin.com/album/D20130702/hairstyles-for-oval-shaped-faces1-921202_H165451_S.jpg" height="50" width="50" /></td>
      <td><img src="https://si0.twimg.com/profile_images/3528477267/a5d136b09d331805e88d24f69c0d0fdb.jpeg" height="50" width="50" /></td>
      <td><img src="http://31.media.tumblr.com/avatar_8f99bee205d9_64.png" height="50" width="50" /></td>
      <td><img src="http://imalbum.aufeminin.com/album/D20130621/919480_YATQJ5UWKKEBPFBMUSOT8XOYQYADGF_hairstyles-for-square-faces1_H000444_S.jpg" height="50" width="50" /></td>
    </tr>
  </table>

  <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
  
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
  <script language='Javascript'>turkSetAssignmentID();</script>
 </body>
</html>
]]>
  </HTMLContent>
  <FrameHeight>600</FrameHeight>
</HTMLQuestion>
''',
    'Reward' : {
        'Amount' : 0.01,
        'CurrencyCode' : 'USD'
        },
    'AssignmentDurationInSeconds' : 24*60*60,
    'LifetimeInSeconds' : 24*60*60,
    'AutoApprovalDelayInSeconds' : 0,
    'RequesterAnnotation': 'My Annotated UUID',
    }

# Content:
# http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/FormattedContentXHTMLSubset.xsd

'''
    <FormattedContent><![CDATA[
       <table>
       <tr>
       <td>Was it this one?</td>
       <td><img="http://54.244.230.230/wordpress/wp-content/uploads/2013/09/safelyStored2.png" /></td>
       </tr>
       </table>
    ]]></FormattedContent>    
'''

single_question_create_options = {
    'Title' : 'My Test Hit',
    'Description' : 'Lots of details',
    'Question' : 
'''
<QuestionForm xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd">
  <Overview>
    <Title>A Title!</Title>
    <Text>Some Text!</Text>
    <Binary>
      <MimeType><Type>image</Type></MimeType>
      <DataURL>http://54.244.230.230/wordpress/wp-content/uploads/2013/09/safelyStored2.png</DataURL>
      <AltText>Missing Image</AltText>
    </Binary>
  </Overview>
  <Question>
    <QuestionIdentifier>not_face</QuestionIdentifier>
     <QuestionContent><Text>Question 1</Text></QuestionContent>
     <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>1</MinSelectionCount>
        <MaxSelectionCount>1</MaxSelectionCount>
        <StyleSuggestion>radiobutton</StyleSuggestion>

        <Selections>
          <Selection>
          <SelectionIdentifier>not_face_selection</SelectionIdentifier>
          <Text>Check here if one of the above images is not a face</Text>
          </Selection>

          <Selection>
          <SelectionIdentifier>two_face_selection</SelectionIdentifier>
          <Text>Check here if there are two different people</Text>
          </Selection>

          <Selection>
          <SelectionIdentifier>recognize_selection</SelectionIdentifier>
    <FormattedContent><![CDATA[
       <table>
       <tr>
       <td>Was it this one?</td>
       <td><img src="http://54.244.230.230/wordpress/wp-content/uploads/2013/09/safelyStored2.png" alt="Missing Image" /></td>
       </tr>
       </table>
    ]]></FormattedContent>              
          </Selection>

        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
</QuestionForm>
''',
    'Reward' : {
        'Amount' : 0.01,
        'CurrencyCode' : 'USD'
        },
    'AssignmentDurationInSeconds' : 24*60*60,
    'LifetimeInSeconds' : 24*60*60,
    'AutoApprovalDelayInSeconds' : 0,
    'RequesterAnnotation': 'My Annotated UUID',
    }

multi_question_create_options = {
    'Title' : 'My Test Hit',
    'Description' : 'Lots of details',
    'Question' : 
'''
<QuestionForm xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionForm.xsd">
  <Overview>
    <Title>A Title!</Title>
    <Text>Some Text!</Text>
    <Binary>
      <MimeType><Type>image</Type></MimeType>
      <DataURL>http://54.244.230.230/wordpress/wp-content/uploads/2013/09/safelyStored2.png</DataURL>
      <AltText>Missing Image</AltText>
    </Binary>
  </Overview>
  <Question>
    <QuestionIdentifier>not_face</QuestionIdentifier>
     <QuestionContent><Text>Question 1</Text></QuestionContent>
     <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <Selection>
          <SelectionIdentifier>not_face_selection</SelectionIdentifier>
          <Text>Check here if one of the above images is not a face</Text>
          </Selection>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
  <Question>
    <QuestionIdentifier>two_face</QuestionIdentifier>
    <QuestionContent><Text>Question 2</Text></QuestionContent>
    <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <Selection>
          <SelectionIdentifier>two_face_selection</SelectionIdentifier>
          <Text>Check here if there are photos of two or more different people.</Text>
          </Selection>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
  <Question>
    <QuestionIdentifier>recognized_face</QuestionIdentifier>
    <QuestionContent><Text>Question 3</Text></QuestionContent>
    <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <Selection>
          <SelectionIdentifier>recognized_face_selection</SelectionIdentifier>
          <Text>Click here if the picture are the same as the one to the right.</Text>
          </Selection>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
</QuestionForm>
''',
    'Reward' : {
        'Amount' : 0.01,
        'CurrencyCode' : 'USD'
        },
    'AssignmentDurationInSeconds' : 24*60*60,
    'LifetimeInSeconds' : 24*60*60,
    'AutoApprovalDelayInSeconds' : 0,
    'RequesterAnnotation': 'My Annotated UUID',
    }

# Create the HIT
#result = mt.create_request( 'CreateHIT', html_create_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'CreateHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'03c10496-31f3-41a4-b5c0-a737d14ce923')])), (u'HIT', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'HITId', u'2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'), (u'HITTypeId', u'2KO0FK0COK2NLFUI0PB9ORW6ONHQJB')]))]))])


get_options = {
    'HITId' : '28RZJMJUNU8P6KZIBLWRC8D8UX5G0E'
    }

result = mt.create_request( 'GetHIT', get_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'GetHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'2ffdd107-2f2f-4d54-b013-44f57ca00ecc')])), (u'HIT', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'HITId', u'2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'), (u'HITTypeId', u'2KO0FK0COK2NLFUI0PB9ORW6ONHQJB'), (u'HITGroupId', u'2HGWQIHPCGJ6KG9ZE1WXK0KQR1P714'), (u'CreationTime', u'2013-10-24T05:04:18Z'), (u'Title', u'My Test Hit'), (u'Description', u'Lots of details'), (u'Question', u'<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">\n  <HTMLContent><![CDATA[\n<!DOCTYPE html>\n<html>\n <head>\n  <meta http-equiv=\'Content-Type\' content=\'text/html; charset=UTF-8\'/>\n  <script type=\'text/javascript\' src=\'https://s3.amazonaws.com/mturk-public/externalHIT_v1.js\'></script>\n </head>\n <body>\n  <form name=\'mturk_form\' method=\'post\' id=\'mturk_form\' action=\'https://www.mturk.com/mturk/externalSubmit\'>\n  <input type=\'hidden\' value=\'\' name=\'assignmentId\' id=\'assignmentId\'/>\n  <h1>What\'s up?</h1>\n  <p><textarea name=\'comment\' cols=\'80\' rows=\'3\'></textarea></p>\n  <p><input type=\'submit\' id=\'submitButton\' value=\'Submit\' /></p></form>\n  <script language=\'Javascript\'>turkSetAssignmentID();</script>\n </body>\n</html>\n]]>\n  </HTMLContent>\n  <FrameHeight>450</FrameHeight>\n</HTMLQuestion>'), (u'HITStatus', u'Reviewable'), (u'MaxAssignments', u'1'), (u'Reward', OrderedDict([(u'Amount', u'0.01'), (u'CurrencyCode', u'USD'), (u'FormattedPrice', u'$0.01')])), (u'AutoApprovalDelayInSeconds', u'0'), (u'Expiration', u'2013-10-25T05:04:18Z'), (u'AssignmentDurationInSeconds', u'86400'), (u'RequesterAnnotation', u'My Annotated UUID'), (u'HITReviewStatus', u'NotReviewed')]))]))])

#NOTE - It took a while for the system to auto approve the task, it
#was at least 10 seconds.
# (u'HITReviewStatus', u'NotReviewed') - NotReviewed, MarkedForReview, ReviewedAppropriate, ReviewedInappropriate
# (u'HITStatus', u'Reviewable') - Assignable, Unassignable, Reviewable, Reviewing, Disposed

get_assignments_options = {
    'HITId' : '2NA8SV7WGKCG2ZTENFU3PHAP1WI1RQ'
    }

#result = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'GetAssignmentsForHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'e966dd16-6639-4be3-894a-ed4da3de6621')])), (u'GetAssignmentsForHITResult', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'NumResults', u'1'), (u'TotalNumResults', u'1'), (u'PageNumber', u'1'), (u'Assignment', OrderedDict([(u'AssignmentId', u'2V12HECWA6X752KNQ53P8KXPUA4LKK'), (u'WorkerId', u'A2UAN9XAD1587R'), (u'HITId', u'2NA8SV7WGKCG2ZTENFU3PHAP1WI1RQ'), (u'AssignmentStatus', u'Submitted'), (u'AutoApprovalTime', u'2013-10-24T08:19:51Z'), (u'AcceptTime', u'2013-10-24T08:09:19Z'), (u'SubmitTime', u'2013-10-24T08:19:51Z'), (u'Answer', u'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<QuestionFormAnswers xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd">\n<Answer>\n<QuestionIdentifier>answer</QuestionIdentifier>\n<FreeText>recognized_face</FreeText>\n</Answer>\n</QuestionFormAnswers>')]))]))]))])


dispose_options = {
    'HITId' : '2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'
    }
# This deletes a HIT.
# result = mt.create_request( 'DisposeHIT', get_assignments_options )

print type( result )

import pprint

pp = pprint.PrettyPrinter( indent=4 )

pp.pprint( result )
