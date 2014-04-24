ROOT ?= /deploy
LVL  ?= staging
APP   = vib

FILES = $(shell git ls-tree -r master --name-only)

# Install the dependencies required for Popeye
#
# This target should be run as root, ie.:
#   sudo make install_deps
#
PYPKGS=\
	boto==2.25.0 \
	web.py \
	wsgilog \
	sqlalchemy==0.9.1 \
	requests \
	pytz \
	mixpanel-py \
	supervisor \
	pillow

PIP_PYPKGS=\
	qtfaststart \
	config

install_deps:
	/usr/bin/apt-get -y install python-pip python-dev python-scipy
	/usr/bin/easy_install $(PYPKGS)
	/usr/local/bin/pip install $(PIP_PYPKGS)
	/usr/bin/apt-get -y install python-mysqldb
	/usr/bin/apt-get -y install apache2
	/usr/bin/apt-get -y install libapache2-mod-wsgi
	/usr/bin/apt-get -y install python-bs4
	/usr/bin/apt-get -y install imagemagick
	/usr/local/bin/pip install xmltodict

# Build the image suitable for software upgrade
package:
	tar zcf package.tar.gz $(FILES)

# This target is called by the sw installer on the target machine.  Does
# what is required to install the new software and activate it.
install:
	mkdir -p /mnt/faces/; chmod oug+rw /mnt/faces/
	mkdir -p $(ROOT)/$(LVL)/$(APP).next
	tar zxf package.tar.gz -C $(ROOT)/$(LVL)/$(APP).next
	( cd $(ROOT)/$(LVL)/$(APP).next; make install_deps )
	-rm -rf $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP) $(ROOT)/$(LVL)/$(APP).prev
	-mv $(ROOT)/$(LVL)/$(APP).next $(ROOT)/$(LVL)/$(APP)
	( cd $(ROOT)/$(LVL); chown -R www-data:www-data $(APP) )
	( cp $(ROOT)/$(LVL)/$(APP)/config/boto.config ~www-data/.boto ; chown www-data:www-data ~www-data/.boto )
	ln -sf $(ROOT)/$(LVL)/$(APP)/deployment/init.d/supervisor-$(LVL) /etc/init.d/supervisor
	( cd /etc/init.d ; /usr/sbin/update-rc.d supervisor defaults )

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
