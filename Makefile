LVL=staging
deploy:
	-rm -rf /deploy/$(LVL)/brewtus.prev
	-rm -rf /deploy/$(LVL)/popeye.prev
	-mv /deploy/$(LVL)/brewtus /deploy/$(LVL)/brewtus.prev
	-mv /deploy/$(LVL)/popeye /deploy/$(LVL)/popeye.prev
	tar --exclude node_modules -zcf - brewtus popeye | \
		(cd /deploy/$(LVL); tar zxf -)
	( cd /deploy/$(LVL)/brewtus; npm install )
