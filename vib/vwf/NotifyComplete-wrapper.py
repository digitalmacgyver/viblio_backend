#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/FaceDetect.conf

from vib.vwf.NotifyComplete.Notify import Notify

while Notify().run(): pass
