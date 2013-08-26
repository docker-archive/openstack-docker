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

# Install OpenStack-Docker Nova Driver
# Go to https://review.openstack.org/#/c/40759/
# Follow the instructions to get the last patchset
# NOTE: This won't be needed anymore as soon as this review is merged
```

That's it!


How can I start a container with the image I want?
--------------------------------------------------

By default, the container is started using the ubuntu image, but you can use
the user_data field to actually spawn anything you want.

From Horizon, when creating the instance, go to the tab "Post-Creation" and
put the following info in the "Customization Script" text area:

```
#docker
image: centos
cmd: "while true; do date ; sleep 1; done"
```

This will start a container using the CentOS image and run display the date
every 1 second (you can verify this in the logs).

Note: that you can use the "cmd" field to spawn anything more useful such as
a opensshd or an apache daemon.


How the Docker driver works?
----------------------------

The Nova driver embeds a tiny HTTP client which talks with the Docker internal
Rest API through a unix socket. It uses the API to control containers and fetch
information about them.

By using an embbeded registry[1], Docker can push and pull images into Glance.
The registry usually lives in a container (see the DevStack support[2]).


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
if the image is authored properly via a Dockerfile[3].


References
----------

1. https://github.com/dotcloud/docker-registry
2. https://review.openstack.org/#/c/40759/
3. http://docs.docker.io/en/latest/use/builder/
