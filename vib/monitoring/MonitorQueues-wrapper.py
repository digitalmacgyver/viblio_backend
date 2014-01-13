#!/usr/bin/env python

import vib.vwf.Monitor

vib.vwf.Monitor.Monitor().update_cloudwatch()
vib.vwf.Monitor.Monitor().set_queue_depth_for_scaling()
