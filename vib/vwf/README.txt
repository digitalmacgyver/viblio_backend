OVERVIEW
======================================================================

We use boto's Amazon SWF library to manage the workflow of our video
pipeline.

The pipeline logic is in VideoProcessingDecider.py.

Each pipeline stage defined in VideoProcessingWorfklow.py will
eventually have its own worker class.

Each stage accepts its parameters as a JSON string in the input
parameter, and returns its output in a JSON string by calling
self.complete( results='JSON STRING' ).

Each worker class follows a similar pattern of boilerplate to interact
with boto/SWF.

CONFIGURATION
======================================================================
The scripts in this directory require the BOTO_CONFIG environment
variable to point at this directory, so it can find the boto.config
file.

Run:

source setup-env.sh

In Bourne/Korn/Bash shells to do this.



