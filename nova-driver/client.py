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

import functools
import httplib
import json
import socket

from nova.openstack.common import log as logging


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


class Response(object):
    def __init__(self, http_response, skip_body=False):
        self._response = http_response
        self.code = int(http_response.status)
        self.data = http_response.read()
        self.json = self._decode_json(self.data)

    def read(self, size=None):
        return self._response.read(size)

    @filter_data
    def _decode_json(self, data):
        if self._response.getheader('Content-Type') != 'application/json':
            return
        try:
            return json.loads(self.data)
        except ValueError:
            return


class UnixHTTPConnection(httplib.HTTPConnection):
    def __init__(self, unix_socket):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.unix_socket)
        self.sock = sock


class DockerHTTPClient(object):
    def __init__(self, unix_socket=None):
        if unix_socket is None:
            unix_socket = '/var/run/docker.sock'
        self._unix_socket = unix_socket

    def is_daemon_running(self):
        try:
            self.list_containers()
            return True
        except socket.error:
            return False

    def make_request(self, *args, **kwargs):
        conn = UnixHTTPConnection(self._unix_socket)
        headers = {}
        if 'headers' in kwargs:
            headers = kwargs['headers']
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
            kwargs['headers'] = headers
        conn.request(*args, **kwargs)
        return Response(conn.getresponse())

    def list_containers(self, _all=True):
        resp = self.make_request(
            'GET',
            '/v1.4/containers/ps?all={0}&limit=50'.format(int(_all)))
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
            'PortSpecs': [],
            'Tty': True,
            'OpenStdin': True,
            'StdinOnce': False,
            'Env': None,
            'Cmd': [],
            'Dns': None,
            'Image': 'ubuntu',
            'Volumes': {},
            'VolumesFrom': '',
        }
        data.update(args)
        resp = self.make_request(
            'POST',
            '/v1.4/containers/create',
            body=json.dumps(data))
        if resp.code != 201:
            return
        obj = json.loads(resp.data)
        for k, v in obj.iteritems():
            if k.lower() == 'id':
                return v

    def start_container(self, container_id):
        resp = self.make_request(
            'POST',
            '/v1.4/containers/{0}/start'.format(container_id),
            body='{}')
        return (resp.code == 200)

    def inspect_image(self, image_name):
        resp = self.make_request(
            'GET',
            '/v1.4/images/{0}/json'.format(image_name))
        if resp.code != 200:
            return
        return resp.json

    def inspect_container(self, container_id):
        resp = self.make_request(
            'GET',
            '/v1.4/containers/{0}/json'.format(container_id))
        if resp.code != 200:
            return
        return resp.json

    def stop_container(self, container_id, timeout=None):
        if timeout is None:
            timeout = 5
        resp = self.make_request(
            'POST',
            '/v1.4/containers/{0}/stop?t={1}'.format(container_id, timeout))
        return (resp.code == 204)

    def destroy_container(self, container_id):
        resp = self.make_request(
            'DELETE',
            '/v1.4/containers/{0}'.format(container_id))
        return (resp.code == 204)

    def pull_repository(self, name):
        parts = name.rsplit(':', 1)
        url = '/v1.4/images/create?fromImage={0}'.format(parts[0])
        if len(parts) > 1:
            url += '&tag={0}'.format(parts[1])
        resp = self.make_request('POST', url)
        while True:
            buf = resp.read(1024)
            if not buf:
                # Image pull completed
                break
        return (resp.code == 200)

    def get_container_logs(self, container_id):
        resp = self.make_request(
            'POST',
            ('/v1.4/containers/{0}/attach'
             '?logs=1&stream=0&stdout=1&stderr=1').format(container_id))
        if resp.code != 200:
            return
        return resp.data

    def get_registry_port(self):
        registry = None
        for container in self.list_containers(_all=False):
            container = self.inspect_container(container['id'])
            path = container['Path']
            env = container['Config']['Env']
            if 'docker-registry' in path:
                registry = container
                break
        if not registry:
            return
        # The registry service always binds on port 5000 in the container.
        return container['NetworkSettings']['PortMapping']['Tcp']['5000']
