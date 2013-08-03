LVL=staging
deploy:
	-rm -rf /deploy/$(LVL)/brewtus.prev
	-rm -rf /deploy/$(LVL)/popeye.prev
	-mv /deploy/$(LVL)/brewtus /deploy/$(LVL)/brewtus.prev
	-mv /deploy/$(LVL)/popeye /deploy/$(LVL)/popeye.prev
	tar --exclude node_modules -zcf - brewtus popeye | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL)/brewtus; npm install )

# Execute this only once when you are building
# a new development machine.  Execute it with sudo:
#
#  sudo make development
#
development:
	( cd brewtus; npm install -g; chmod oug+rw ~/.npm; npm install; chmod oug+rw node_modules )
	( cd popeye; make install_deps )
	mkdir -p /deploy/development
	chmod -R oug+rw /deploy
	ln -s `pwd`/brewtus /deploy/development/
	ln -s `pwd`/popeye /deploy/development/
	ln -s /deploy/development/brewtus/brewtus-development.init.d /etc/init.d/brewtus
	ln -s /deploy/development/popeye/deployment/init.d/popeye-development /etc/init.d/popeye
	( cd /etc/init.d; update-rc.d brewtus defaults; update-rc.d popeye defaults )
	/etc/init.d/brewtus start
	/etc/init.d/popeye start
