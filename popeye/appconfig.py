"""
A simple dev/stage/production configuration file handler, based
on the config python module.

Put all of your application configuration in a file called
'whatever'.config.  This is your base configuration, the one
used if there is no DEPLOYMENT environment variable set.
This might represent the development environment.  Let's
say you have a variable in whatever.config:

foo: 'bar'
log: '/tmp/base.log'

Then in your python program:

from appconfig import AppConfig
c = AppConfig( 'whatever' ).config()
print( c.log )
>> /tmp/base.log
print( c.foo )
>> bar

Now create another config file, called staging.config.  In tis file:

log: '/tmp/staging.log'

You don't need to specify "foo", it will be common.  Only specify the
things you need to be different.  This time set DEPLOYMENT=staging in
the shell before you run your program.  The same code will now yeild:

from appconfig import AppConfig
c = AppConfig( 'whatever' ).config()
print( c.log )
>> /tmp/staging.log
print( c.foo )
>> bar

So basically you define a base .config with all your config values,
then a number of other .config files with over-writes.  Use the
DEPLOYMENT environment variable to pick the right set of over-writes.
This DEPLOYMENT variable would normally be set in the /etc/init.d boot
time script that runs your program in production.

"""
import os
from config import Config, ConfigMerger
import logging

# Our app config needs to decide which config
# files to read; development, staging or production.
# It does this based on a DEPLOYMENT env variable.
# But when running under Apache/WSGI, there are no
# env variables, so we use the wsgi process-group
# name to determine what mode we are in:
try:
    import mod_wsgi
    os.environ['DEPLOYMENT'] = mod_wsgi.process_group
except:
    pass

class AppConfig:
    def __init__(self, basename):
        basefile = basename+'.config'
        try:
            base = Config( basefile )
            base.addNamespace(logging)
        except Exception, e:
            raise Exception( 'Cannot open/read/parse %s: %s' % (basefile, str(e)) )

        if 'DEPLOYMENT' in os.environ:
            deployment = os.environ['DEPLOYMENT']+'.config'
            try:
                dep = Config( deployment )
                dep.addNamespace(logging)
            except Exception, e:
                raise Exception( 'Cannot open/read/parse %s: %s' % (deployment, str(e)) )

            try:
                ConfigMerger(lambda m1,m2,key: "overwrite").merge( base, dep)
            except Exception, e:
                raise Exception( 'Failed to merge %s and %s: %s' % (basefile, deployment, str(e)) )
            
        self.base = base

    def config(self):
        return self.base

