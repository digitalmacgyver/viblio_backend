# make LVL=<staging|prod|local>
LVL ?= staging

deploy: deploy_brewtus deploy_popeye deploy_utils deploy_vib

deploy_brewtus:
	mkdir -p /deploy/$(LVL)
	mkdir -p /mnt/uploaded_files/errors; chmod oug+rw /mnt/uploaded_files/errors
	-rm -rf /deploy/$(LVL)/brewtus.prev
	-mv /deploy/$(LVL)/brewtus /deploy/$(LVL)/brewtus.prev
	tar --exclude node_modules --exclude '*.pyc' -zcf - brewtus | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL)/brewtus; npm install )
	( cd /deploy/$(LVL); chown -R www-data:www-data brewtus )

deploy_popeye:
	mkdir -p /deploy/$(LVL)
	mkdir -p /mnt/uploaded_files/errors; chmod oug+rw /mnt/uploaded_files/errors
	-rm -rf /deploy/$(LVL)/popeye.prev
	-mv /deploy/$(LVL)/popeye /deploy/$(LVL)/popeye.prev
	tar --exclude node_modules --exclude '*.pyc' -zcf - popeye | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL); chown -R www-data:www-data popeye )

deploy_utils:
	mkdir -p /deploy/$(LVL)
	-rm -rf /deploy/$(LVL)/utils.prev
	-mv /deploy/$(LVL)/utils /deploy/$(LVL)/utils.prev
	tar --exclude node_modules --exclude '*.pyc' -zcf - utils | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL); chown -R www-data:www-data utils )

deploy_vib:
	mkdir -p /deploy/$(LVL)
	-rm -rf /deploy/$(LVL)/vib.prev
	-mv /deploy/$(LVL)/vib /deploy/$(LVL)/vib.prev
	tar --exclude node_modules --exclude '*.pyc' -zcf - vib | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL); chown -R www-data:www-data vib )
	( cp /deploy/$(LVL)/vib/vwf/boto.config ~www-data/.boto ; chown www-data:www-data ~www-data/.boto )


# Execute this only once when you are building
# a new development machine.  Execute it with sudo:
#
#  sudo make development
#
development: exiftool
	( cd brewtus; npm install -g; chmod oug+rw ~/.npm; npm install; chmod oug+rw node_modules )
	( cd popeye; make install_deps )
	mkdir -p /mnt/uploaded_files; chmod oug+rw /mnt/uploaded_files
	mkdir -p /mnt/uploaded_files/errors; chmod oug+rw /mnt/uploaded_files/errors
	mkdir -p /deploy/local
	chmod -R oug+rw /deploy
	make LVL=local deploy
	ln -s /deploy/local/brewtus/brewtus-local.init.d /etc/init.d/brewtus
	ln -s /deploy/local/popeye/deployment/init.d/popeye-local /etc/init.d/popeye
	ln -s /deploy/local/popeye/deployment/init.d/supervisor-local /etc/init.d/supervisor
	( cd /etc/init.d; update-rc.d brewtus defaults; update-rc.d popeye defaults; update-rc.d supervisor defaults )
	/etc/init.d/brewtus start
	/etc/init.d/popeye start
	/etc/init.d/supervisor start

exiftool:
	( cd /tmp; \
	  wget http://www.sno.phy.queensu.ca/~phil/exiftool/Image-ExifTool-9.36.tar.gz; \
	  tar zxf Image-ExifTool-9.36.tar.gz; \
	  cd Image-ExifTool-9.36 ; \
	  /usr/bin/perl Makefile.PL; \
	  make test && make install)
