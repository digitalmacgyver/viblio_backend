import os


def get_confidence(video_file,working_dir,model_dir):
    path= os.path.dirname( __file__ ) + '/../../../object_classification/classification/viblio/projects/viblio_classification/'
    python_path = os.path.dirname( __file__ ) + '/../../../object_classification/classification/'
    os.system("cd %s; PYTHONPATH=$PYTHONPATH:%s ./video_classifier.sh %s %s %s" %(path,python_path,video_file,working_dir,model_dir) )
    with open(working_dir+'/result.txt') as f:
        confidence=float(f.readlines[0])
    print 'confidence value ',confidence
    return confidence
