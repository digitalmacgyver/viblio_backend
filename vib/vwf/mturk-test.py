#!/usr/bin/env python

# Create hello world HIT.

from mturkcore import MechanicalTurk

mt = MechanicalTurk( 
    { 
        'use_sandbox'           : True, 
        'stdout_log'            : True, 
        'aws_key'     : 'AKIAJHD46VMHB2FBEMMA',
        'aws_secret_key' : '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',
        } 
    )

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
  <form name='mturk_form' method='post' id='mturk_form' action='https://www.mturk.com/mturk/externalSubmit'>
  



  <input type='hidden' value='' name='assignmentId' id='assignmentId'/>
  <h1>What's up?</h1>
  <p><textarea name='comment' cols='80' rows='3'></textarea></p>
  <p><input type='submit' id='submitButton' value='Submit' /></p></form>
  <script language='Javascript'>turkSetAssignmentID();</script>
 </body>
</html>
]]>
  </HTMLContent>
  <FrameHeight>450</FrameHeight>
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

question_create_options = {
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
  </Overview>
  <Question>
    <QuestionIdentifier>not_face</QuestionIdentifier>
 
    <FormattedContent><![CDATA[
       <table>
       <tr>
       <td>Was it this one?</td>
       <td><img="http://54.244.230.230/wordpress/wp-content/uploads/2013/09/safelyStored2.png" /></td>
       </tr>
       </table>
    ]]></FormattedContent>    

    <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <SelectionIdentifier>not_face_selection</SelectionIdentifier>
          <Text>Check here if one of the above images is not a face</Text>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
  <Question>
    <QuestionIdentifier>two_face</QuestionIdentifier>
    <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <SelectionIdentifier>two_face_selection</SelectionIdentifier>
          <Text>Check here if there are photos of two or more different people.</Text>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
  <Question>
    <QuestionIdentifier>recognized_face</QuestionIdentifier>
    <AnswerSpecification>
      <SelectionAnswer>
        <MinSelectionCount>0</MinSelectionCount>
        <StyleSuggestion>checkbox</StyleSuggestion>
        <Selections>
          <SelectionIdentifier>recognized_face_selection</SelectionIdentifier>
          <Text>Click here if the picture are the same as the one to the right.</Text>
        </Selections>
      </SelectionAnswer>
    </AnswerSpecification>
  </Question>
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
result = mt.create_request( 'CreateHIT', question_create_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'CreateHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'03c10496-31f3-41a4-b5c0-a737d14ce923')])), (u'HIT', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'HITId', u'2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'), (u'HITTypeId', u'2KO0FK0COK2NLFUI0PB9ORW6ONHQJB')]))]))])


get_options = {
    'HITId' : '2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'
    }

#result = mt.create_request( 'GetHIT', get_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'GetHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'2ffdd107-2f2f-4d54-b013-44f57ca00ecc')])), (u'HIT', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'HITId', u'2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'), (u'HITTypeId', u'2KO0FK0COK2NLFUI0PB9ORW6ONHQJB'), (u'HITGroupId', u'2HGWQIHPCGJ6KG9ZE1WXK0KQR1P714'), (u'CreationTime', u'2013-10-24T05:04:18Z'), (u'Title', u'My Test Hit'), (u'Description', u'Lots of details'), (u'Question', u'<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">\n  <HTMLContent><![CDATA[\n<!DOCTYPE html>\n<html>\n <head>\n  <meta http-equiv=\'Content-Type\' content=\'text/html; charset=UTF-8\'/>\n  <script type=\'text/javascript\' src=\'https://s3.amazonaws.com/mturk-public/externalHIT_v1.js\'></script>\n </head>\n <body>\n  <form name=\'mturk_form\' method=\'post\' id=\'mturk_form\' action=\'https://www.mturk.com/mturk/externalSubmit\'>\n  <input type=\'hidden\' value=\'\' name=\'assignmentId\' id=\'assignmentId\'/>\n  <h1>What\'s up?</h1>\n  <p><textarea name=\'comment\' cols=\'80\' rows=\'3\'></textarea></p>\n  <p><input type=\'submit\' id=\'submitButton\' value=\'Submit\' /></p></form>\n  <script language=\'Javascript\'>turkSetAssignmentID();</script>\n </body>\n</html>\n]]>\n  </HTMLContent>\n  <FrameHeight>450</FrameHeight>\n</HTMLQuestion>'), (u'HITStatus', u'Reviewable'), (u'MaxAssignments', u'1'), (u'Reward', OrderedDict([(u'Amount', u'0.01'), (u'CurrencyCode', u'USD'), (u'FormattedPrice', u'$0.01')])), (u'AutoApprovalDelayInSeconds', u'0'), (u'Expiration', u'2013-10-25T05:04:18Z'), (u'AssignmentDurationInSeconds', u'86400'), (u'RequesterAnnotation', u'My Annotated UUID'), (u'HITReviewStatus', u'NotReviewed')]))]))])

#NOTE - It took a while for the system to auto approve the task, it
#was at least 10 seconds.
# (u'HITReviewStatus', u'NotReviewed') - NotReviewed, MarkedForReview, ReviewedAppropriate, ReviewedInappropriate
# (u'HITStatus', u'Reviewable') - Assignable, Unassignable, Reviewable, Reviewing, Disposed

get_assignments_options = {
    'HITId' : '2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'
    }

#result = mt.create_request( 'GetAssignmentsForHIT', get_assignments_options )
#<class 'collections.OrderedDict'>
#OrderedDict([(u'GetAssignmentsForHITResponse', OrderedDict([(u'OperationRequest', OrderedDict([(u'RequestId', u'175d899f-f1ac-4f03-bb1b-b61127f75173')])), (u'GetAssignmentsForHITResult', OrderedDict([(u'Request', OrderedDict([(u'IsValid', u'True')])), (u'NumResults', u'1'), (u'TotalNumResults', u'1'), (u'PageNumber', u'1'), (u'Assignment', OrderedDict([(u'AssignmentId', u'2A85R98D8J3ZLL433YEYFG3MDCLVF7'), (u'WorkerId', u'A2UAN9XAD1587R'), (u'HITId', u'2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'), (u'AssignmentStatus', u'Approved'), (u'AutoApprovalTime', u'2013-10-24T05:08:15Z'), (u'AcceptTime', u'2013-10-24T05:08:08Z'), (u'SubmitTime', u'2013-10-24T05:08:15Z'), (u'ApprovalTime', u'2013-10-24T05:10:05Z'), (u'Answer', u'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<QuestionFormAnswers xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd">\n<Answer>\n<QuestionIdentifier>comment</QuestionIdentifier>\n<FreeText>Not much.</FreeText>\n</Answer>\n</QuestionFormAnswers>')]))]))]))])

dispose_options = {
    'HITId' : '2Q2SSZVXX2Q8C82V1TPGQIW1YJ1O6N'
    }
# This deletes a HIT.
# result = mt.create_request( 'DisposeHIT', get_assignments_options )

print type( result )

import pprint

pp = pprint.PrettyPrinter( indent=4 )

pp.pprint( result )
