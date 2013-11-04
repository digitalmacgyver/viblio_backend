#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/*/Transcode.conf

from vib.vwf.Transcode.Transcode import Transcode

while Transcode().run(): pass
