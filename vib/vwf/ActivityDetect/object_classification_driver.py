import os


def get_confidence(video_file,working_dir,model_dir):
    path= '../../../object_classification/classification/projects/viblio_classification/'
    python_path = '../../../object_classification/classification/'
    os.system("cd %s; PYTHONPATH=$PYTHONPATH:%s ./viblio_classifier.sh %s %s %s" %(path,python_path,video_file,working_dir,model_dir) )
    with open(working_dir+'/results.txt') as f:
        confidence=float(f.readlines[0])
    print 'confidence value ',confidence
    return confidence
