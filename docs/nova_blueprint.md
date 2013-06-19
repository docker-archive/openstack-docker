Add a new hypervisor to support Docker containers
=================================================


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


What does Docker bring to the current libvirt/lxc support?
----------------------------------------------------------

The question about whether it is better to support an hypervisor natively or
through libvirt was being asked already for XenAPI vs Libvirt/Xen[2].

Some answers apply for Docker as well, for instance, to quote libvirt again:

"the goal of libvirt: to provide a common generic and stable layer to securely
manage domains on a node. [...] This implies ... that some very specific
capabilities which are not generic enough may not be provided as libvirt
APIs.”[3]

Docker takes advantage of LXC and the AUFS file system to offer specific
capabilities which are definitely not generic enough to be provided by libvirt:

* Process-level API: For example docker can collect the standard outputs and
  inputs of the process running in each container for logging or direct
  interaction, it allows blocking on a container until it exits, setting its
  environment, and other process-oriented primitives which don’t fit well in
  libvirt’s abstraction.
* Advanced change control at the filesystem level: Every change made on the
  filesystem is managed through a set of layers[4] which can be snapshotted,
  rolled back, diff-ed etc.
* Image portability: The state of any docker container can be optionally
  committed as an image and shared through a central image registry [5].
  Docker images are designed to be portable across infrastructures, so they are
  a great building block for hybrid cloud scenarios.
* Build facility: docker can automate the assembly of a container from an
  application’s source code. This gives developers an easy way to deploy
  payloads to an Openstack cluster as part of their development workflow [6].


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
2. https://wiki.openstack.org/wiki/XenAPI#Discussion
3. http://libvirt.org/goals.html
4. http://docs.docker.io/en/latest/commandline/command/diff/
5. http://docs.docker.io/en/latest/use/workingwithrepository/
6. http://docs.docker.io/en/latest/use/builder/
