import commands
import os


def activity_present(video_file,working_dir,model_dir):
    path= os.path.dirname( __file__ ) + '/../../../object_classification/classification/viblio/projects/viblio_classification/'
    python_path = os.path.dirname( __file__ ) + '/../../../object_classification/classification/'

    ( status, output ) = commands.getstatusoutput("cd %s; PYTHONPATH=$PYTHONPATH:%s ./video_classifier.sh %s %s %s" % (path,python_path,video_file,working_dir,model_dir) )
    confidence = -1

    if status != 0 and status != 256:
        raise Exception( "Error, unexpected return status from viblio_classifier.sh, return value was %s output was: %s" % ( status, output ) )

    try:
        confidence = float( output )
    except:
        raise Exception( "Error, failed to convert viblio_classifier.sh output to float, output was: %s" % ( output ) )

    return ( status, confidence )
