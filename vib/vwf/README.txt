OVERVIEW
======================================================================

We use boto's Amazon SWF library to manage the workflow of our video
pipeline.

The pipeline logic is in VPDecider.py.

Each pipeline stage defined in VPWorfklow.py will eventually have its
own worker class.

Each worker class follows a similar pattern of boilerplate similar to
FaceDetect.py to interact with boto/SWF.  All that must be done is:
1) Create a new class derived from VWorker

2) Assign a member variable of that class to the relevant activity
type in VPWorkflow

3) Implement the run_task method.  run_task takes in a Python
dictionary of arguments on input, and returns a Python dictionary of
arguments for the next stage.  run_task can notify the pipeline of an
error by returning a Python dictionary that contains the
ACTIVITY_ERROR key.  If it does this, the truth value of the "retry"
key in the return will specify if this task should be tried again or
if the error is fatal.

CONFIGURATION
======================================================================
The scripts in this directory require the BOTO_CONFIG environment
variable to point at this directory, and that the vib directory by in
the PYTHONPATH.

Run:

source setup-env.sh

In Bourne/Korn/Bash shells to do this.



