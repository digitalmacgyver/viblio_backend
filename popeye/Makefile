# Install the dependencies required for Popeye
#
# This target should be run as root, ie.:
#   sudo make install_deps
#
PYPKGS=\
	boto \
	web.py \
	wsgilog \
	config \
	sqlalchemy \
	requests \
	qtfaststart \
	pytz \
	mixpanel-py \
	supervisor \
	pillow

install_deps:
	apt-get -y install python-pip python-dev
	easy_install $(PYPKGS)
	apt-get -y install python-mysqldb
	apt-get -y install apache2
	apt-get -y install libapache2-mod-wsgi
	apt-get -y install python-bs4
	pip install xmltodict

