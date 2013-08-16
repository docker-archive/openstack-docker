# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2013 dotCloud, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
A Docker Hypervisor which allows running Linux Containers instead of VMs.
"""

import base64
import os
import random
import socket
import time

from oslo.config import cfg

from nova.compute import power_state
from nova import exception
from nova.openstack.common import log
from nova import utils
from nova.virt.docker import client
from nova.virt.docker import hostinfo
from nova.virt import driver


CONF = cfg.CONF
CONF.import_opt('host', 'nova.netconf')

LOG = log.getLogger(__name__)


class DockerDriver(driver.ComputeDriver):
    capabilities = {
        'has_imagecache': True,
        'supports_recreate': True,
    }

    """Docker hypervisor driver."""

    def __init__(self, virtapi, read_only=False):
        super(DockerDriver, self).__init__(virtapi)
        self.docker = client.DockerHTTPClient()
        self.virtapi = virtapi
        self.fake = False

    def use_mock_client(self):
        """Replace HTTP Client with the Mock one (useful for unit tests)."""
        self.docker = client.MockClient()
        self.fake = True

    def init_host(self, host):
        if self.docker.is_daemon_running() is False:
            raise exception.NovaException("Docker daemon is not running or is "
                    "not reachable (check the rights on /var/run/docker.sock)")

    def list_instances(self, _inspect=False):
        res = []
        for container in self.docker.list_containers():
            info = self.docker.inspect_container(container['id'])
            if _inspect:
                res.append(info)
            else:
                res.append(info['Config'].get('Hostname'))
        return res

    def legacy_nwinfo(self):
        return True

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks."""
        pass

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks."""
        pass

    def find_container_by_name(self, name):
        for info in self.list_instances(_inspect=True):
            if info['Config'].get('Hostname') == name:
                return info
        return {}

    def get_info(self, instance):
        container = self.find_container_by_name(instance['name'])
        if not container:
            raise exception.InstanceNotFound(instance_id=instance['name'])
        running = container['State'].get('Running')
        info = {
            'max_mem': 0,
            'mem': 0,
            'num_cpu': 1,
            'cpu_time': 0
        }
        info['state'] = power_state.RUNNING if running \
            else power_state.SHUTDOWN
        return info

    def get_host_stats(self, refresh=False):
        hostname = socket.gethostname()
        memory = hostinfo.get_memory_usage()
        disk = hostinfo.get_disk_usage()
        stats = self.get_available_resource(hostname)
        stats['hypervisor_hostname'] = hostname
        stats['host_hostname'] = hostname
        stats['host_name_label'] = hostname
        return stats

    def get_available_resource(self, nodename):
        memory = hostinfo.get_memory_usage()
        disk = hostinfo.get_disk_usage()
        stats = {
            'vcpus': 1,
            'vcpus_used': 0,
            'memory_mb': memory['total'] / (1024 ** 2),
            'memory_mb_used': memory['used'] / (1024 ** 2),
            'local_gb': disk['total'] / (1024 ** 3),
            'local_gb_used': disk['used'] / (1024 ** 3),
            'disk_available_least': disk['available'] / (1024 ** 3),
            'hypervisor_type': 'docker',
            'hypervisor_version': '1.0',
            'hypervisor_hostname': nodename,
            'cpu_info': '?'
        }
        return stats

    def _find_cgroup_devices_path(self):
        for ln in open('/proc/mounts'):
            if ln.startswith('cgroup ') and 'devices' in ln:
                return ln.split(' ')[1]

    def _find_container_pid(self, container_id):
        cgroup_path = self._find_cgroup_devices_path()
        lxc_path = os.path.join(cgroup_path, 'lxc')
        tasks_path = os.path.join(lxc_path, container_id, 'tasks')
        n = 0
        while True:
            if n > 20:
                return
            try:
                with open(tasks_path) as f:
                    pids = f.readlines()
                    if pids:
                        return int(pids[0].strip())
            except IOError:
                pass
            time.sleep(0.5)
            n += 1

    def _setup_network(self, instance, network_info):
        if self.fake is True or not network_info:
            return
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        network_info = network_info[0]
        netns_path = '/var/run/netns'
        if not os.path.exists(netns_path):
            utils.execute(
                'mkdir', '-p', netns_path, run_as_root=True)
        nspid = self._find_container_pid(container_id)
        if not nspid:
            raise RuntimeError(
                'Cannot find any PID under '
                'container "{0}"'.format(container_id))
        netns_path = os.path.join(netns_path, container_id)
        utils.execute(
            'ln', '-sf', '/proc/{0}/ns/net'.format(nspid),
            '/var/run/netns/{0}'.format(container_id),
            run_as_root=True)
        rand = random.randint(0, 100000)
        if_local_name = 'pvnetl{0}'.format(rand)
        if_remote_name = 'pvnetr{0}'.format(rand)
        bridge = network_info[0]['bridge']
        ip = network_info[1]['ips'][0]['ip']
        utils.execute(
            'ip', 'link', 'add', 'name', if_local_name, 'type',
            'veth', 'peer', 'name', if_remote_name,
            run_as_root=True)
        utils.execute(
            'brctl', 'addif', bridge, if_local_name,
            run_as_root=True)
        utils.execute(
            'ip', 'link', 'set', if_local_name, 'up',
            run_as_root=True)
        utils.execute(
            'ip', 'link', 'set', if_remote_name, 'netns', nspid,
            run_as_root=True)
        utils.execute(
            'ip', 'netns', 'exec', container_id, 'ifconfig',
            if_remote_name, ip,
            run_as_root=True)

    def _parse_user_data(self, user_data):
        data = {}
        user_data = base64.b64decode(user_data)
        for ln in user_data.split('\n'):
            ln = ln.strip()
            if not ln or ':' not in ln:
                continue
            if ln.startswith('#'):
                continue
            ln = ln.split(':', 1)
            data[ln[0].strip()] = ln[1].strip('"\' ')
        return data

    def _get_memory_limit_bytes(self, instance):
        for metadata in instance.get('system_metadata', []):
            if not metadata['deleted'] and \
                    metadata['key'] == 'instance_type_memory_mb':
                        return int(metadata['value']) * 1024 * 1024
        return 0

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        cmd = ['/bin/sh']
        user_data = instance.get('user_data')
        image_name = 'ubuntu'
        if user_data:
            user_data = self._parse_user_data(user_data)
            if 'cmd' in user_data:
                cmd = ['/bin/sh', '-c', user_data.get('cmd')]
            if 'image' in user_data:
                image_name = user_data.get('image')
        args = {
            'Hostname': instance['name'],
            'Image': image_name,
            'Cmd': cmd,
            'Memory': self._get_memory_limit_bytes(instance)
        }
        container_id = self.docker.create_container(args)
        if container_id is None:
            LOG.info('Image name "{0}" does not exist, fetching it...'.format(
                image_name))
            res = self.docker.pull_repository(image_name)
            if res is False:
                raise exception.InstanceDeployFailure(
                    'Cannot pull missing image',
                    instance_id=instance['name'])
            container_id = self.docker.create_container(args)
            if container_id is None:
                raise exception.InstanceDeployFailure(
                    'Cannot create container',
                    instance_id=instance['name'])
        self.docker.start_container(container_id)
        try:
            self._setup_network(instance, network_info)
        except Exception as e:
            raise exception.InstanceDeployFailure(
                'Cannot setup network: {0}'.format(e),
                instance_id=instance['name'])

    def destroy(self, instance, network_info, block_device_info=None,
                destroy_disks=True):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.stop_container(container_id)
        self.docker.destroy_container(container_id)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.stop_container(container_id)
        self.docker.start_container(container_id)

    def power_on(self, context, instance, network_info, block_device_info):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.start_container(container_id)

    def power_off(self, instance):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        self.docker.stop_container(container_id)

    def get_console_output(self, instance):
        container_id = self.find_container_by_name(instance['name']).get('id')
        if not container_id:
            return
        return self.docker.get_container_logs(container_id)
