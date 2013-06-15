# vim: tabstop=4 shiftwidth=4 softtabstop=4

import datetime
import functools
import httplib
import json
import random
import socket
import string
import time
from urlparse import urlparse

try:
    from nova.openstack.common import log as logging
except ImportError:
    import logging


LOG = logging.getLogger(__name__)


def filter_data(f):
    """Decorator that post-processes data returned by Docker to avoid any
       surprises with different versions of Docker
    """
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        out = f(*args, **kwds)

        def _filter(obj):
            if isinstance(obj, list):
                new_list = []
                for o in obj:
                    new_list.append(_filter(o))
                obj = new_list
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, basestring):
                        obj[k.lower()] = v
            return obj
        return _filter(out)
    return wrapper


class MockClient(object):
    def __init__(self, endpoint=None):
        self._containers = {}

    def _fake_id(self):
        return ''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for x in range(64))

    def is_daemon_running(self):
        return True

    @filter_data
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

    @filter_data
    def inspect_container(self, container_id):
        if container_id not in self._containers:
            return
        container = self._containers[container_id]
        info = {
            'Args': [],
            'Config': container['config'],
            'Created': str(datetime.datetime.utcnow()),
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
                'StartedAt': str(datetime.datetime.utcnow())
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


class Response(object):
    def __init__(self, http_response, skip_body=False):
        self.code = int(http_response.status)
        if skip_body is True:
            self._consume_body(http_response)
            return
        self.data = http_response.read()
        self.json = self._decode_json(http_response, self.data)

    def _consume_body(self, http_response):
        while True:
            buf = http_response.read(1024)
            if not buf:
                return

    @filter_data
    def _decode_json(self, http_response, data):
        if http_response.getheader('Content-Type') != 'application/json':
            return
        try:
            return json.loads(self.data)
        except ValueError:
            return


class HTTPClient(object):
    def __init__(self, endpoint=None):
        if endpoint is None:
            endpoint = 'http://localhost:4243'
        url = urlparse(endpoint)
        self._http_conn = httplib.HTTPConnection(url.hostname, url.port)

    def is_daemon_running(self):
        try:
            self.list_containers()
            return True
        except socket.error:
            return False

    def list_containers(self, _all=True):
        self._http_conn.request(
            'GET',
            '/containers/ps?all={0}&limit=50'.format(int(_all)))
        resp = Response(self._http_conn.getresponse())
        return resp.json

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
        self._http_conn.request(
            'POST',
            '/containers/create',
            body=json.dumps(data),
            headers={'Content-Type': 'application/json'})
        resp = Response(self._http_conn.getresponse())
        if resp.code != 201:
            return
        obj = json.loads(resp.data)
        for k, v in obj.iteritems():
            if k.lower() == 'id':
                return v

    def start_container(self, container_id):
        self._http_conn.request(
            'POST',
            '/containers/{0}/start'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 200)

    def inspect_container(self, container_id):
        self._http_conn.request(
            'GET',
            '/containers/{0}/json'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        if resp.code != 200:
            return
        return resp.json

    def stop_container(self, container_id, timeout=None):
        if timeout is None:
            timeout = 5
        self._http_conn.request(
            'POST',
            '/containers/{0}/stop?t={1}'.format(container_id, timeout))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 204)

    def destroy_container(self, container_id):
        self._http_conn.request(
            'DELETE',
            '/containers/{0}'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 204)

    def pull_repository(self, name):
        self._http_conn.request(
            'POST',
            '/images/create?fromImage={0}'.format(name))
        resp = Response(self._http_conn.getresponse(), skip_body=True)
        return (resp.code == 200)

    def get_container_logs(self, container_id):
        self._http_conn.request(
            'POST',
            '/containers/{0}/attach?logs=1&stream=0&stdout=1&stderr=1'.format(
                container_id))
        resp = Response(self._http_conn.getresponse())
        if resp.code != 200:
            return
        return resp.data
