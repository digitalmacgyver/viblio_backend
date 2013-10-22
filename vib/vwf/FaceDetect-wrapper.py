#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/FaceDetect.conf

from vib.vwf.FaceDetect import FaceDetect

while FaceDetect().run(): pass
