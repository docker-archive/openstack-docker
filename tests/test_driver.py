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

from nova import test
from nova.tests import utils
from nova.tests.virt.test_virt_drivers import test_virt_drivers


class DockerDriverTestCase(test_virt_drivers._VirtDriverTestCase, test.TestCase):
    def setUp(self):
        # Point _VirtDriverTestCase at the right module
        self.driver_module = 'nova.virt.docker.DockerDriver'
        super(DockerDriverTestCase, self).setUp()
        # Replace connection to Docker daemon with in-memory Mock object
        self.connection.use_mock_client()

    #NOTE(bcwaldon): This exists only because _get_running_instance on the
    # base class will not let us set a custom disk/container_format.
    def _get_running_instance(self):
        instance_ref = utils.get_test_instance()
        network_info = utils.get_test_network_info(legacy_model=False)
        network_info[0]['network']['subnets'][0]['meta']['dhcp_server'] = \
            '1.1.1.1'
        image_info = utils.get_test_image_info(None, instance_ref)
        image_info['disk_format'] = 'raw'
        image_info['container_format'] = 'docker'
        self.connection.spawn(self.ctxt, instance_ref, image_info,
                              [], 'herp', network_info=network_info)
        return instance_ref, network_info
