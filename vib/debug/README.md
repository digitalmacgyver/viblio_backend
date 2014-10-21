# Debugging the Video Pipeline

When there are errors in the video pipeline they are sent to the
Loggly service. 

The scripts in this directory can be used to identify files which had
errors, and summarize the events which led up to those errors.

## Usage

* Edit the get_reports_script.py to set the n_hours parameter for how
  far back we will search for errors.

* A subdirectory called "reports" will be created, within this
  directory:
  * A .txt file for each unique mediafile which had an error
  * The name of the file is the media_uuid of the file which had an error
  * The contents are ordered by message time, so you can follow the
    flow of execution for that file.