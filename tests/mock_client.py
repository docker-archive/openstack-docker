import random
import string
import time

from nova.openstack.common import timeutils
import nova.virt.docker.client


class MockClient(object):
    def __init__(self, endpoint=None):
        self._containers = {}

    def _fake_id(self):
        return ''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for x in range(64))

    def is_daemon_running(self):
        return True

    @nova.virt.docker.client.filter_data
    def list_containers(self, _all=True):
        containers = []
        for container_id, container in self._containers.iteritems():
            containers.append({
                'Status': 'Exit 0',
                'Created': int(time.time()),
                'Image': 'ubuntu:12.04',
                'Ports': '',
                'Command': 'bash ',
                'Id': container_id
            })
        return containers

    def create_container(self, args):
        data = {
            'Hostname': '',
            'User': '',
            'Memory': 0,
            'MemorySwap': 0,
            'AttachStdin': False,
            'AttachStdout': False,
            'AttachStderr': False,
            'PortSpecs': None,
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': 'ubuntu',
            'Volumes': {},
            'VolumesFrom': ''
        }
        data.update(args)
        container_id = self._fake_id()
        self._containers[container_id] = {
            'id': container_id,
            'running': False,
            'config': args
        }
        return container_id

    def start_container(self, container_id):
        if container_id not in self._containers:
            return False
        self._containers[container_id]['running'] = True
        return True

    @nova.virt.docker.client.filter_data
    def inspect_image(self, image_name):
        return {'container_config': {'Cmd': None}}

    @nova.virt.docker.client.filter_data
    def inspect_container(self, container_id):
        if container_id not in self._containers:
            return
        container = self._containers[container_id]
        info = {
            'Args': [],
            'Config': container['config'],
            'Created': str(timeutils.utcnow()),
            'ID': container_id,
            'Image': self._fake_id(),
            'NetworkSettings': {
                'Bridge': '',
                'Gateway': '',
                'IPAddress': '',
                'IPPrefixLen': 0,
                'PortMapping': None
            },
            'Path': 'bash',
            'ResolvConfPath': '/etc/resolv.conf',
            'State': {
                'ExitCode': 0,
                'Ghost': False,
                'Pid': 0,
                'Running': container['running'],
                'StartedAt': str(timeutils.utcnow())
            },
            'SysInitPath': '/tmp/docker',
            'Volumes': {},
        }
        return info

    def stop_container(self, container_id, timeout=None):
        if container_id not in self._containers:
            return False
        self._containers[container_id]['running'] = False
        return True

    def destroy_container(self, container_id):
        if container_id not in self._containers:
            return False
        del self._containers[container_id]
        return True

    def pull_repository(self, name):
        return True

    def get_container_logs(self, container_id):
        if container_id not in self._containers:
            return False
        return '\n'.join([
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ',
            'Vivamus ornare mi sit amet orci feugiat, nec luctus magna ',
            'vehicula. Quisque diam nisl, dictum vitae pretium id, ',
            'consequat eget sapien. Ut vehicula tortor non ipsum ',
            'consectetur, at tincidunt elit posuere. In ut ligula leo. ',
            'Donec eleifend accumsan mi, in accumsan metus. Nullam nec ',
            'nulla eu risus vehicula porttitor. Sed purus ligula, ',
            'placerat nec metus a, imperdiet viverra turpis. Praesent ',
            'dapibus ornare massa. Nam ut hendrerit nunc. Interdum et ',
            'malesuada fames ac ante ipsum primis in faucibus. ',
            'Fusce nec pellentesque nisl.'])

    def get_registry_port(self):
        return 5042



