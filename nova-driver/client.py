# vim: tabstop=4 shiftwidth=4 softtabstop=4

import socket
import httplib
from urlparse import urlparse
import json
try:
    from nova.openstack.common import log as logging
except ImportError:
    import logging


LOG = logging.getLogger(__name__)


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

    def _filter_data(self, obj):
        """ All data returned are post-processed to avoid surprises with
            different versions of Docker
        """
        if isinstance(obj, list):
            new_list = []
            for o in obj:
                new_list.append(self._filter_data(o))
            obj = new_list
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, basestring):
                    obj[k.lower()] = v
        return obj

    def _decode_json(self, http_response, data):
        if http_response.getheader('Content-Type') != 'application/json':
            return
        try:
            obj = json.loads(self.data)
            obj = self._filter_data(obj)
            return obj
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
        self._http_conn.request('GET',
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
        self._http_conn.request('POST',
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
        self._http_conn.request('POST',
                '/containers/{0}/start'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 200)

    def inspect_container(self, container_id):
        self._http_conn.request('GET',
                '/containers/{0}/json'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        if resp.code != 200:
            return
        return resp.json

    def stop_container(self, container_id, timeout=None):
        if timeout is None:
            timeout = 5
        self._http_conn.request('POST',
                '/containers/{0}/stop?t={1}'.format(container_id, timeout))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 204)

    def destroy_container(self, container_id):
        self._http_conn.request('DELETE',
                '/containers/{0}'.format(container_id))
        resp = Response(self._http_conn.getresponse())
        return (resp.code == 204)

    def pull_repository(self, name):
        self._http_conn.request('POST',
                '/images/create?fromImage={0}'.format(name))
        resp = Response(self._http_conn.getresponse(), skip_body=True)
        return (resp.code == 200)

    def get_container_logs(self, container_id):
        self._http_conn.request('POST',
                '/containers/{0}/attach?logs=1&stream=0&stdout=1&stderr=1' \
                        .format(container_id))
        resp = Response(self._http_conn.getresponse())
        if resp.code != 200:
            return
        return resp.data
