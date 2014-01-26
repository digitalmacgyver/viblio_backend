#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/*/ActivityDetect.conf

from vib.vwf.ActivityDetect.Detect import Detect

while Detect().run(): pass
