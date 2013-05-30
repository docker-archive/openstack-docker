# vim: tabstop=4 shiftwidth=4 softtabstop=4

import functools
import hashlib
import httplib
import urllib
import json

import glance.openstack.common.log as logging
from glance.openstack.common import timeutils


LOG = logging.getLogger(__name__)
IMAGES_CACHE = []


def log_call(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        LOG.info(_('Calling %(funcname)s: args=%(args)s, kwargs=%(kwargs)s') %
                 {"funcname": func.__name__,
                  "args": args,
                  "kwargs": kwargs})
        try:
            output = func(*args, **kwargs)
            LOG.info(_('Returning %(funcname)s: %(output)s') %
                     {"funcname": func.__name__,
                      "output": output})
            return output
        except Exception as e:
            LOG.exception(type(e))
    return wrapped


def _make_uuid(val):
    """ Generate a fake UUID from a string to be compliant with the API
        It uses a MD5 to return the same UUID for a given string.
    """
    h = hashlib.md5(val).hexdigest()
    return '{0}-{1}-{2}-{3}-{4}'.format(
            h[:8], h[8:12], h[12:16], h[16:20], h[20:])


def _image_format(image_name, **values):
    dt = timeutils.utcnow()
    image = {
        'id': _make_uuid(image_name),
        'name': image_name,
        'owner': None,
        'locations': [],
        'status': 'active',
        'protected': False,
        'is_public': True,
        'container_format': 'docker',
        'disk_format': 'docker',
        'min_ram': 0,
        'min_disk': 0,
        'size': 0,
        'checksum': None,
        'tags': [],
        'created_at': dt,
        'updated_at': dt,
        'deleted_at': None,
        'deleted': False,
    }
    properties = values.pop('properties', {})
    properties = [{'name': k,
                   'value': v,
                   'deleted': False} for k, v in properties.items()]
    image['properties'] = properties
    image.update(values)
    return image


def _docker_search(term):
    """ Interface to the Docker search API """
    http_conn = httplib.HTTPConnection('localhost', 4243)
    http_conn.request('GET',
            '/images/search?term={0}'.format(urllib.quote(term)))
    resp = http_conn.getresponse()
    data = resp.read()
    if resp.status != 200:
        return []
    return [repos['Name'] for repos in json.loads(data)]


def _init_cache():
    global IMAGES_CACHE
    if not IMAGES_CACHE:
        IMAGES_CACHE = _docker_search('library')


def reset():
    pass


def setup_db_env(*args, **kwargs):
    pass


@log_call
def image_get(context, image_id, session=None, force_show_deleted=False):
    images = [_image_format(i) for i in IMAGES_CACHE]
    for i in images:
        if i['id'] == image_id:
            return i


@log_call
def image_get_all(context, filters=None, marker=None, limit=None,
                  sort_key='created_at', sort_dir='desc',
                  member_status='accepted', is_public=None):
    _init_cache()
    return [_image_format(i) for i in IMAGES_CACHE]


@log_call
def image_property_create(context, values):
    pass


@log_call
def image_property_delete(context, prop_ref, session=None):
    pass


@log_call
def image_member_find(context, image_id=None, member=None, status=None):
    pass


@log_call
def image_member_create(context, values):
    pass


@log_call
def image_member_update(context, member_id, values):
    pass


@log_call
def image_member_delete(context, member_id):
    pass


@log_call
def image_create(context, image_values):
    global IMAGES_CACHE
    _init_cache()
    name = image_values.get('name')
    if not name:
        return
    if '/' in name:
        IMAGES_CACHE.append(name)
    else:
        images = _docker_search(name)
        if not images:
            return
        for i in images:
            if i not in IMAGES_CACHE:
                IMAGES_CACHE.append(i)
    return _image_format(name)


@log_call
def image_update(context, image_id, image_values, purge_props=False):
    pass


@log_call
def image_destroy(context, image_id):
    pass


@log_call
def image_tag_get_all(context, image_id):
    pass


@log_call
def image_tag_get(context, image_id, value):
    pass


@log_call
def image_tag_set_all(context, image_id, values):
    pass


@log_call
def image_tag_create(context, image_id, value):
    pass


@log_call
def image_tag_delete(context, image_id, value):
    pass


def is_image_mutable(context, image):
    return False


def is_image_sharable(context, image, **kwargs):
    return True


def is_image_visible(context, image, status=None):
    return True
