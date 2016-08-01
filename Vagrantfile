# -*- mode: ruby -*-
# vi: set ft=ruby :
VAGRANTFILE_API_VERSION=2
PROJECT_NAME = "lehaproxy"
CLIENT_MEMORY=1024
CLIENT_CPU_COUNT = 2
CLIENT_IOAPIC = "on"
CLIENT_NAT_DNS_HOSTRESOLVER="on"
SERVER_MEMORY=2048
SERVER_CPU_COUNT = 2
SERVER_IOAPIC = "on"
SERVER_NAT_DNS_HOSTRESOLVER="on"
ENVS = {
    'PROJECT_NAME'            => PROJECT_NAME,
    'PROJECT_TZ'              => "Europe/Amsterdam",
    'PROJECT_CLIENT_HOSTNAME' => PROJECT_NAME + ".local",
    'PROJECT_SERVER_HOSTNAME' => "boulder.local",
    'PROJECT_SERVER_IP'       => "192.168.33.111",
    'PROJECT_CLIENT_IP'       => "192.168.33.222"
}

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    config.hostmanager.enabled = true
    config.hostmanager.manage_host = true
    config.vbguest.auto_update = true
    config.vbguest.no_remote = false
    config.vm.synced_folder ".", "/vagrant", enabled: true
    config.vm.synced_folder ".", "/" + PROJECT_NAME + "/", type: "virtualbox"

    config.vm.define "boulder", autostart: true do |server|
        server.vm.box = "ubuntu/trusty64"
        server.vm.hostname = "boulder.local"
        server.vm.network :private_network, ip:  ENVS['PROJECT_SERVER_IP']
        server.vm.provision "shell" do |s|
            s.path = './provisioning_server.sh'
            # s.env = ENVS
        end
        server.vm.provider :virtualbox do |vb|
            vb.customize ["modifyvm", :id, "--memory", SERVER_MEMORY]
            vb.customize ["modifyvm", :id, "--cpus", SERVER_CPU_COUNT]
            vb.customize ["modifyvm", :id, "--ioapic", SERVER_IOAPIC]
            vb.customize ["modifyvm", :id, "--natdnshostresolver1", SERVER_NAT_DNS_HOSTRESOLVER]
        end
    end

    config.vm.define "lehaproxy", autostart: true do |client|
        client.vm.box = "debian/jessie64"
        client.vm.hostname = PROJECT_NAME + ".local"
        client.vm.network :private_network, ip:  ENVS['PROJECT_CLIENT_IP']
        client.vm.provision "shell" do |s|
            s.path = './provisioning_client.sh'
            # s.env = ENVS
        end
        client.vm.provider :virtualbox do |vb|
            vb.customize ["modifyvm", :id, "--memory", CLIENT_MEMORY]
            vb.customize ["modifyvm", :id, "--cpus", CLIENT_CPU_COUNT]
            vb.customize ["modifyvm", :id, "--ioapic", CLIENT_IOAPIC]
            vb.customize ["modifyvm", :id, "--natdnshostresolver1", CLIENT_NAT_DNS_HOSTRESOLVER]
        end
    end
end
