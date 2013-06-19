# vim: tabstop=4 shiftwidth=4 softtabstop=4

import os


def get_disk_usage():
    # This is the location where Docker stores its containers. It's currently
    # hardcoded in Docker so it's not configurable yet.
    docker_path = '/var/lib/docker'
    if not os.path.exists(docker_path):
        docker_path = '/'
    st = os.statvfs(docker_path)
    return {
        'total': st.f_blocks * st.f_frsize,
        'available': st.f_bavail * st.f_frsize,
        'used': (st.f_blocks - st.f_bfree) * st.f_frsize
    }


def parse_meminfo():
    meminfo = {}
    with open('/proc/meminfo') as f:
        for ln in f:
            parts = ln.split(':')
            if len(parts) < 2:
                continue
            key = parts[0].lower()
            value = parts[1].strip()
            parts = value.split(' ')
            value = parts[0]
            if not value.isdigit():
                continue
            value = int(parts[0])
            if len(parts) > 1 and parts[1] == 'kB':
                value *= 1024
            meminfo[key] = value
    return meminfo


def get_memory_usage():
    meminfo = parse_meminfo()
    total = meminfo.get('memtotal', 0)
    free = meminfo.get('memfree', 0)
    free += meminfo.get('cached', 0)
    free += meminfo.get('buffers', 0)
    return {
        'total': total,
        'free': free,
        'used': total - free
    }
