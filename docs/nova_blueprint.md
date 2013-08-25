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


How the Docker driver works?
----------------------------

The Nova driver embeds a tiny HTTP client which talks with the Docker internal
Rest API through a unix socket. It uses the API to control containers and fetch
information about them.

By using an embbeded registry[7], Docker can push and pull images into Glance.
The registry usually lives in a container (see the DevStack support[8]).


How to use it?
--------------

Once you configured Nova to use the docker driver, the flow is the same as any
other driver.

```
$ glance image-list
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
| ID                                   | Name                            | Disk Format | Container Format | Size     | Status |
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
| f5049d8b-93cf-49ab-af56-e70d89da4cf4 | cirros-0.3.1-x86_64-uec         | ami         | ami              | 25165824 | active |
| 0f1ec86c-157f-4f22-9889-c07cf7bb601c | cirros-0.3.1-x86_64-uec-kernel  | aki         | aki              | 4955792  | active |
| 03a54807-2e35-4864-a337-458c3eeb77e6 | cirros-0.3.1-x86_64-uec-ramdisk | ari         | ari              | 3714968  | active |
| 77083f3c-d320-46e3-bcba-0cb4f5a55e7b | docker-busybox:latest           | raw         | docker           | 2271596  | active |
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
```

Only images with a "docker" container format will be bootable. The image
contains basically a tarball of the container filesystem.

NOTE: Docker supports inheritance between images, so it's possible to have
several "docker" images without a name (None). It's usually an image
dependence. These images are bootable as well, the filesystem will basically
have a previous state. But it's probably not what you want to use in the first
place.

It's recommended to add new images to Glance by using Docker. For instance,
here is how you can fetch images from the public registry and push them back
to Glance in order to boot a Nova instance with it:

```
$ docker search hipache
Found 3 results matching your query ("hipache")
NAME                             DESCRIPTION
samalba/hipache                  https://github.com/dotcloud/hipache
```

Then, tag the image with the docker-registry location and push it.

```
$ docker tag samalba/hipache 10.0.2.15:5042/hipache
$ docker push samalba/hipache 10.0.2.15:5042/hipache
The push refers to a repository [10.0.2.15:5042/hipache] (len: 1)
Sending image list
Pushing repository 10.0.2.15:5042/hipache (1 tags)
Push 100% complete
```

Note that "10.0.2.15" is the IP address of my host, it would definitely work
with "localhost" since my docker-registry is inside a container (however the
port is important).

In this case, the docker-registry (running in a docker container with a port
mapped on 5042) will push the images to Glance. From there Nova can reach them
and you can verify it with the glance cli.

```
$ glance image-list
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
| ID                                   | Name                            | Disk Format | Container Format | Size     | Status |
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
| f5049d8b-93cf-49ab-af56-e70d89da4cf4 | cirros-0.3.1-x86_64-uec         | ami         | ami              | 25165824 | active |
| 0f1ec86c-157f-4f22-9889-c07cf7bb601c | cirros-0.3.1-x86_64-uec-kernel  | aki         | aki              | 4955792  | active |
| 03a54807-2e35-4864-a337-458c3eeb77e6 | cirros-0.3.1-x86_64-uec-ramdisk | ari         | ari              | 3714968  | active |
| 77083f3c-d320-46e3-bcba-0cb4f5a55e7b | docker-busybox:latest           | raw         | docker           | 2271596  | active |
| 998f52ba-fe03-46b0-b5a6-4b5f29427bcb | hipache:latest                  | raw         | docker           | 486      | active |
+--------------------------------------+---------------------------------+-------------+------------------+----------+--------+
```

You can obviously boot instances from nova cli:

```
$ nova boot --image "docker-busybox:latest" --flavor m1.tiny test
+--------------------------------------+--------------------------------------+
| Property                             | Value                                |
+--------------------------------------+--------------------------------------+
| OS-EXT-STS:task_state                | scheduling                           |
| image                                | docker-busybox:latest                |
| OS-EXT-STS:vm_state                  | building                             |
| OS-EXT-SRV-ATTR:instance_name        | instance-0000002d                    |
| OS-SRV-USG:launched_at               | None                                 |
| flavor                               | m1.micro                             |
| id                                   | 31086c50-f937-4f80-9790-045096ecb32c |
| security_groups                      | [{u'name': u'default'}]              |
| user_id                              | 1a3eed38d1344e869dd019b3636db12b     |
| OS-DCF:diskConfig                    | MANUAL                               |
| accessIPv4                           |                                      |
| accessIPv6                           |                                      |
| progress                             | 0                                    |
| OS-EXT-STS:power_state               | 0                                    |
| OS-EXT-AZ:availability_zone          | nova                                 |
| config_drive                         |                                      |
| status                               | BUILD                                |
| updated                              | 2013-08-25T00:22:32Z                 |
| hostId                               |                                      |
| OS-EXT-SRV-ATTR:host                 | None                                 |
| OS-SRV-USG:terminated_at             | None                                 |
| key_name                             | None                                 |
| OS-EXT-SRV-ATTR:hypervisor_hostname  | None                                 |
| name                                 | test                                 |
| adminPass                            | QwczSPAAT6Mm                         |
| tenant_id                            | 183a9b7ed7c6465f97387458d693ca4c     |
| created                              | 2013-08-25T00:22:31Z                 |
| os-extended-volumes:volumes_attached | []                                   |
| metadata                             | {}                                   |
+--------------------------------------+--------------------------------------+
```

Once the instance is booted:

```
$ nova list
+--------------------------------------+------+--------+------------+-------------+------------------+
| ID                                   | Name | Status | Task State | Power State | Networks         |
+--------------------------------------+------+--------+------------+-------------+------------------+
| 31086c50-f937-4f80-9790-045096ecb32c | test | ACTIVE | None       | Running     | private=10.0.0.2 |
+--------------------------------------+------+--------+------------+-------------+------------------+
```

You can also see the corresponding container on docker:

```
$ docker ps
docker ps
ID              IMAGE                                  COMMAND      CREATED             STATUS          PORTS
f337c7fec5ff    10.0.2.15:5042/docker-busybox:latest   sh           10 seconds ago      Up 10 seconds
```

The command used here is the one configured in the image. Each container image
can have a command configured for the run. The driver does not override this.
You can image booting an apache2 instance, it will start the apache process
if the image is authored properly via a Dockerfile[6].


References
----------

1. http://www.docker.io/
2. https://wiki.openstack.org/wiki/XenAPI#Discussion
3. http://libvirt.org/goals.html
4. http://docs.docker.io/en/latest/commandline/command/diff/
5. http://docs.docker.io/en/latest/use/workingwithrepository/
6. http://docs.docker.io/en/latest/use/builder/
7. https://github.com/dotcloud/docker-registry
8. https://review.openstack.org/#/c/40759/
