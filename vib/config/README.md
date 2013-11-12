Configuration Data
==================

There are two sets of configuration information in vib/config:
1. The AppConfig module and related configuration files
2. All other configuration

Deployment Conventions
----------------------

By convention, all configuration and software operates in one of three
domains, set via the DEPLOYMENT environment variable:

* local - development software running on developer servers
  * local typically uses some remote resources, such as the same RDS database as staging, and various Amazon cloud services
* staging - pre-production environment hosted in [EC2](http://aws.amazon.com/ec2/) and [RDS](http://aws.amazon.com/rds/)
* prod - production environment hosted on the EC2/RDS and other services in our production [VPC](http://aws.amazon.com/vpc/)

AppConfig
---------

Our configuration module is AppConfig.  You can load the configuration
by adding these to the top of your program:

```
import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()
```

This will load the configuration in vib/config/viblio.conf, overridden
by the contents of prod.config, staging.config, or local.config as
determined by the DEPLOYMENT environment variable.

All application configuration (web service keys, server endpoints,
file paths, queue names, etc.) should be stored in these files.

Other Configuration
-------------------

Configuration which is needed by programs under video_processor/vib
but that can not be managed by the AppConfig module should also be
placed in the vib/config directory.

These are:

* boto.config - The [boto.swf](http://docs.pythonboto.org/en/latest/ref/swf.html) interface we are using doesn't have a good way to specify the AWS region to use in code when using the Layer2 interface, so we use this configuration file
* [Supervisor](http://supervisord.org/) - Process control configuration:
  * For more details read the overview documentation for (vwf)[../vwf/README.md]
  * We use supervisor to manage the execution of various applications, supervisor:
    * Restarts processes when they terminate
    * Controls the number of process of each application type that we run
  * For each DEPLOYMENT environment of local, staging, or prod there is a corresponding supervisor-DEPLOYMENT.conf and vib/config/DEPLOYMENT subdirectory
    * The contents of the vib/config/DEPLOYMENT directory are where the actual configuration for our processes are found
  