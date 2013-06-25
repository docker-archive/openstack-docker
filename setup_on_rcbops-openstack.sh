#!/bin/sh
# - samalba

[ ! $(which nova) ] && {
    echo "ERROR: OpenStack is not installed"
    exit 1
}

docker_check=$(ps -ef | grep -v grep | grep docker)

[ -z "$docker_check" ] && {
    echo "ERROR: Docker is not running or is not installed"
    exit 1
}

ROOT=$(dirname $(readlink -f "$0"))

update_config() {
    file=$1
    key=$2
    value=$3
    grep ^$key $file >/dev/null
    [ $? -eq 0 ] && {
        # Found the pattern, replacing
        sed -i "s/^\($key[ ]*=\).*$/\1 $value/" $file
    } || {
        # Did not find the key, adding it after the beginning of [DEFAULT]
        sed -i "s/^\(\[DEFAULT\].*\)$/\1\n$key = $value/" $file
    }
    echo "Applied changes to $file"
}

install_nova_driver() {
    echo "Installing Docker driver for Nova"
    ln -snf ${ROOT}/nova-driver /usr/lib/python2.7/dist-packages/nova/virt/docker 
    ln -snf ${ROOT}/nova-driver/docker.filters /etc/nova/rootwrap.d/docker.filters
    update_config /etc/nova/nova.conf compute_driver docker.DockerDriver
}

install_glance_backend() {
    echo "Installing Docker image backend for Glance"
    ln -snf ${ROOT}/glance-db-backend /usr/lib/python2.7/dist-packages/glance/db/docker
    update_config /etc/glance/glance-registry.conf data_api glance.db.docker.api
}

install_nova_driver
install_glance_backend
echo "Please restart 'nova-compute' and 'glance-registry'"
