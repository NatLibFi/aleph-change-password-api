
Vagrant.configure("2") do |config|
 
  config.vm.box = "ubuntu/trusty64"

  config.vm.synced_folder ".", "/vagrant"
  
  config.vm.network "forwarded_port", guest: 80, host: 8080

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y apache2 python-pip python-dev libaio1 unzip

    mkdir -p /opt/oracle
    unzip /vagrant/instantclient-basic-linux.x64-12.2.0.1.0.zip -d /opt/oracle

    export LD_LIBRARY_PATH=/opt/oracle/instantclient_12_2:$LD_LIBRARY_PATH
    sudo sh -c "echo /opt/oracle/instantclient_12_2 > /etc/ld.so.conf.d/oracle-instantclient.conf"
    sudo ldconfig

    pip install cx_Oracle
    rm /etc/apache2/sites-available/000-default.conf
    ln -s /vagrant/Vagrantdata/000-default.conf /etc/apache2/sites-available/000-default.conf
    a2enmod cgi
    service apache2 restart

    mkdir -p /exlibris/aleph/a20_2/alephm/
    touch /exlibris/aleph/a20_2/alephm/.cshrc

    mkdir -p /exlibris/aleph/a20_2/aleph/proc/
    ln -s /vagrant/Vagrantdata/p_file_06 /exlibris/aleph/a20_2/aleph/proc/p_file_06

    chmod +x /vagrant/Vagrantdata/p_file_06 /exlibris/aleph/a20_2/aleph/proc/p_file_06
  SHELL
end
