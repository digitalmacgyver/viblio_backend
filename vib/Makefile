ROOT ?= /deploy
LVL  ?= staging
APP   = vwf

FILES = $(shell git ls-tree -r master --name-only)

# Build the image suitable for software upgrade
package:
	tar zcf package.tar.gz $(FILES)

# This target is called by the sw installer on the target machine.  Does
# what is required to install the new software and activate it.
install:
	mkdir -p $(ROOT)/$(LVL)
	mkdir -p /mnt/faces/; chmod oug+rw /mnt/faces/
	mkdir -p $(ROOT)/$(LVL)/$(APP).next
	tar zxf package.tar.gz -C $(ROOT)/$(LVL)/$(APP).next
	-rm -rf $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP) $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP).next $(ROOT)/$(LVL)/$(APP)
	( cp $(ROOT)/$(LVL)/vib/config/boto.config ~www-data/.boto ; chown www-data:www-data ~www-data/.boto )
	( cd $(ROOT)/$(LVL); chown -R www-data:www-data $(APP) )
	ln -s $(ROOT)/$(LVL)/vib/deployment/init.d/supervisor-$(LVL) /etc/init.d/supervisor
	( cd /etc/init.d ; update-rc.d supervisor defaults )
	/etc/init.d supervisor start

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
