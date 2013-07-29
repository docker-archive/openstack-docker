OpenStack-docker: deploy lightweight linux containers on Openstack
==================

[OpenStack](http://en.wikipedia.org/wiki/OpenStack) is
"an Infrastructure as a Service (IaaS) cloud computing project that is free
open source software released under the terms of the Apache License."

You can deploy OpenStack on your physical machines, and then use OpenStack
APIs (which are compatible with AWS APIs) to deploy virtual machines to
run your applications.

[Docker](http://www.docker.io) is "an open-source engine
which automates the deployment of applications as highly portable, self-sufficient
containers which are independent of hardware, language, framework, packaging system
and hosting provider."

You can deploy Docker on your physical or virtual machines, and then run
your apps within containers.

`openstack-docker` is a driver for OpenStack Nova. Just like other drivers
rely on Xen, libvirt, etc. to deploy instances, `openstack-docker` relies on
Docker. When you create OpenStack instances, instead of spinning up
virtual machines, you will be starting containers. The end result is,
that you end up controlling containers using OpenStack's APIs, dashboards,
and overall awesomeness.


Why Is This Cool?
-----------------

If you like containers, if you like OpenStack -- you'll love this!

Why? It allows you to do [Lightweight Virtualization](http://blog.dotcloud.com/scale11)
but by leveraging on the robust APIs of OpenStack. Containers have a lower footprint
(compared to VMs), and they boot much faster. On the other hand, they are containers,
not VMs; so there is less isolation, and they only run Linux processes.

Also, since containers can run on physical, but also virtual machines,
it means that you can run OpenStack to deploy containers on top of e.g.
an EC2 cluster.



How Can I Use It?
-----------------

For the moment, the recommended way is to use an OpenStack development environment
like DevStack. We assume that you already know a bit about running OpenStack,
particularly DevStack.


```
# Install and Run Docker's daemon: http://docs.docker.io/en/latest/use/basics/
sudo docker -d &

# Install DevStack
git clone git://github.com/openstack-dev/devstack.git
cd devstack; ./stack.sh

# Install OpenStack-Docker Nova Driver and Glance Backend
git clone git://github.com/dotcloud/openstack-docker.git
cd openstack-docker && sudo ./setup_on_devstack.sh

# Restart glance-registry and nova-compute from the devstack screen
screen -rd
```

That's it!


What's Under The Hood?
----------------------

Docker exposes a REST API. The driver talks to this REST API.

When you create an instance, a new container is created. That's pretty much it!

If you know Docker and Nova concepts, there are two useful technical bits of info:

- Glance exposes Docker's images but does not store anything (this work is still
  done by Docker itself).
- Both Docker and Nova allocate IP addresses for the containers. So in fact, each
  container will end up having two IP addresses: one allocated by docker, on `eth0`;
  and another one allocated by Nova, on `eth1`. If it's deemed necessary, a future
  version might simplify this and make only one interface visible in containers.
  This is open to discussion.


Can I Use It In Production?
---------------------------

Not yet! The next step is to get some feedback from the OpenStack community.
This is our first OpenStack integration, so it would be surprising if we got
everything right on the first try :-)

Also, Docker itself is not yet production-ready. But it's maturing quickly!


Run Nova unit tests
-------------------

The Nova driver implements a Mock Docker client that allows to use it in
"Fake mode" for unit testing.

From Nova main repository, you can use those unit tests by running:

```
./run_tests.sh --virtual-env-path ~/.virtualenvs/ --virtual-env-name nova nova.tests.virt.test_virt_drivers.DockerDriverTestCase
```

