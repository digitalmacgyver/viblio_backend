sudo /etc/init.d/popeye stop
sudo /etc/init.d/supervisor stop
sudo make LVL=local deploy_popeye deploy_utils deploy_vib
sudo /etc/init.d/popeye start
#sudo /etc/init.d/supervisor start
