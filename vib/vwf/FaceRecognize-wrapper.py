#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/FaceRecognize.conf

from vib.vwf.FaceRecognize.Recognize import Recognize

while Recognize().run(): pass
