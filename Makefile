# make LVL=<staging|prod|local>
LVL ?= staging
deploy:
	mkdir -p /deploy/$(LVL)
	-rm -rf /deploy/$(LVL)/brewtus.prev
	-rm -rf /deploy/$(LVL)/popeye.prev
	-mv /deploy/$(LVL)/brewtus /deploy/$(LVL)/brewtus.prev
	-mv /deploy/$(LVL)/popeye /deploy/$(LVL)/popeye.prev
	tar --exclude node_modules --exclude '*.pyc' -zcf - brewtus popeye | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL)/brewtus; npm install )
	( cd /deploy/$(LVL); chown -R www-data:www-data brewtus; chown -R www-data:www-data popeye )
 
# Execute this only once when you are building
# a new development machine.  Execute it with sudo:
#
#  sudo make development
#
development: exiftool
	( cd brewtus; npm install -g; chmod oug+rw ~/.npm; npm install; chmod oug+rw node_modules )
	( cd popeye; make install_deps )
	mkdir -p /mnt/uploaded_files; chmod oug+rw /mnt/uploaded_files
	mkdir -p /deploy/local
	chmod -R oug+rw /deploy
	make LVL=local deploy
	ln -s /deploy/local/brewtus/brewtus-local.init.d /etc/init.d/brewtus
	ln -s /deploy/local/popeye/deployment/init.d/popeye-local /etc/init.d/popeye
	( cd /etc/init.d; update-rc.d brewtus defaults; update-rc.d popeye defaults )
	/etc/init.d/brewtus start
	/etc/init.d/popeye start

exiftool:
	cd /tmp
	wget http://www.sno.phy.queensu.ca/~phil/exiftool/Image-ExifTool-9.36.tar.gz
	tar zxf Image-ExifTool-9.36.tar.gz
	cd Image-ExifTool-9.36
	/usr/bin/perl Makefile.PL
	make test && make install
