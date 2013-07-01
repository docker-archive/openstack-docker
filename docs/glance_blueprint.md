Add a DB backend to proxify Docker images
=========================================


What is Docker?
---------------

Docker is an open-source engine which automates the deployment of applications
as highly portable, self-sufficient containers which are independent of
hardware, language, framework, packaging system and hosting provider.[1]
Docker extends LXC with a high level API providing a lightweight virtualization
solution that runs processes in isolation. It provides a way to automate
software deployment in a secure and repeatable environment. A Standard
Container in Docker contains a software component along with all of its
dependencies - binaries, libraries, configuration files, scripts, virtualenvs,
jars, gems, tarballs, etc. Docker can be run on any x64 Linux kernel that
supports cgroups and aufs.


Integration of Docker Into Nova
-------------------------------

Through the integration into Nova, we aim to make usage of containers as easy
and powerful as VMs. For some use cases, containers are a better fit than VMs.
For instance, when there is a need to deploy hundreds of instances in a short
amount of time, containers are faster to deploy and have a reduced memory
footprint on the host machine.

The purpose of integrating Docker with Nova is to take the advantage of the
OpenStack infrastructure. Docker is a way of managing LXC containers on a
single machine. However used behind Nova makes it much more powerful since it’s
then possible to manage several hosts which will then manage hundreds of
containers. The current Docker project aims for full OpenStack compatibility.

Containers don't aim to be a replacement for VMs, they are just complementary
in the sense that they are better for specific use cases. Nova support for VMs
is currently advanced thanks to the variety of hypervisors running VMs. However
it's not the case for containers even though libvirt/LXC is a good starting
point. Docker aims to go the second level of integration.


What's the role of Glance on the side of Nova and Docker?
---------------------------------------------------------

Glance implements an API for switchable DB backends. Those backends tells
Glance where to find a specific image and store its meta-data. The role of the
Docker's DB backend is to integrate smoothly all images stored by Docker public
Registry[2] and make them available to any OpenStack project using Glance
(especially Nova with Docker hypervisor enabled).

The DB backend will make it easy to add any specific images as demonstrated on
Docker's blog[3].


What’s next?
------------

As of now, there are currently 76 contributors on Docker’s repository
(including 10 full-time dotCloud employees assigned to Docker), the community
is growing and we’re receiving more and more public contributions. The
OpenStack integration is part of our roadmap and we’re committed to maintain
the code submitted to the core to keep it aligned with the last versions of
Docker.


References
----------

1. http://www.docker.io/
2. https://index.docker.io/
3. http://blog.docker.io/2013/06/openstack-docker-manage-linux-containers-with-nova/
