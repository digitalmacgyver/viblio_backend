#!/usr/bin/env python

# Execution of this file is managed by Supervisor, configuration at
# ../config/VPDecider.conf

from vib.vwf.VPDecider import VPDecider

while VPDecider().run(): pass
