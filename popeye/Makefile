# Install the dependencies required for Popeye
#
# This target should be run as root, ie.:
#   sudo make install_deps
#
PYPKGS=\
	web.py \
	wsgilog \
	config \
	sqlalchemy \
	qtfaststart

install_deps:
	easy_install $(PYPKGS)
	apt-get install python-mysqldb
	apt-get install apache2
	apt-get install libapache2-mod-wsgi
