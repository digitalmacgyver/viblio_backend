#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/FaceRecognize.conf

from vib.vwf.FaceRecognize import FaceRecognize

while FaceRecognize().run(): pass
