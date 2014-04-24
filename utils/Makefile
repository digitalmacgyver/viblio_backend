ROOT ?= /deploy
LVL  ?= staging
APP   = utils

FILES = $(shell git ls-tree -r master --name-only)

# Install the dependencies required for Popeye
#
# This target should be run as root, ie.:
#   sudo make install_deps
#
PYPKGS=\
	sqlalchemy==0.9.1 \

PIP_PYPKGS=\
	config

install_deps:
	/usr/bin/apt-get -y install python-pip python-dev
	/usr/bin/easy_install $(PYPKGS)
	/usr/local/bin/pip install $(PIP_PYPKGS)
	/usr/bin/apt-get -y install python-mysqldb

# Build the image suitable for software upgrade
package:
	tar zcf package.tar.gz $(FILES)

# This target is called by the sw installer on the target machine.  Does
# what is required to install the new software and activate it.
install:
	mkdir -p $(ROOT)/$(LVL)/$(APP).next
	tar zxf package.tar.gz -C $(ROOT)/$(LVL)/$(APP).next
	( cd $(ROOT)/$(LVL)/$(APP).next; make install_deps )
	-rm -rf $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP) $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP).next $(ROOT)/$(LVL)/$(APP)
	( cd $(ROOT)/$(LVL); chown -R www-data:www-data $(APP) )

# bump:
# This will actually run upgrade.pl to initiate a software upgrade.  You must
# indicate which domain to upgrade: LVL=staging or LVL=prod.  If LVL is set to
# prod, you must be on a machine in the VPC that has access to the production
# database.
#
# You can downgrade to a previous version by:
#   upgrade.pl -db $(LVL) -app $(APP) -downgrade <older-version>
#
bump:
	upgrade.pl -db $(LVL) -app $(APP) -bump -f package.tar.gz

# list:
# List our versions
versions:
	upgrade.pl -db $(LVL) -app $(APP) -check
