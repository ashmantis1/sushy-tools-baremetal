=========================
Redfish development tools
=========================

This is a set of simple simulation tools aiming at supporting the
development and testing of the Redfish protocol implementations and,
in particular, Sushy library (https://docs.openstack.org/sushy/). It
is not designed for use outside of development and testing environments.
Please do not run sushy-tools in a production environment of any kind.

The package ships two simulators - static Redfish responder and
virtual Redfish BMC that is backed by libvirt or OpenStack cloud.

The static Redfish responder is a simple REST API server which
responds the same things to client queries. It is effectively
read-only.

The virtual Redfish BMC resembles the real Redfish-controlled bare-metal
machine to some extent. Some client queries are translated to commands that
actually control VM instances simulating bare metal hardware. However some
of the Redfish commands just return static content never touching the
virtualization backend and, for that matter, virtual Redfish BMC is similar
to the static Redfish responder.

This version of this project has included a few more additions. The main feature added
is the ability to control baremetal devices, namely Tapo smart plugs, and Intel AMT.
This functionality is found in the form of the Tapo driver. To use this driver write a config 
as shown in the example below: 

```
[
    {
        u'uuid': u'<name of node>',
        u'name': u'<not used but must be set to something>',
        u'address': u'<Tapo P100 IP',
        u'power_state': u'Off',
        u'amt': False,
        u'last_updated': '',
        u'tapo_username': u'<TP link Username>',
        u'tapo_password': u'<TP Link Password',
        u'nics': [
            {u'address': u'00:5c:52:31:3a:9c'}
        ]
    },
    {
        u'uuid': u'<name of node>',
        u'name': u'<not used but must be set to something>',
        u'power_state': u'Off',
        u'amt': True,
        u'amt_address': u'<AMT static IP address>',
        u'amt_password': u'<AMT Password>',
        u'last_updated': '',
        u'nics': [
            {u'address': u'00:5c:52:31:3a:9c'}
        ]
    },
]
```

After you have your config, you can run this command to get started: 

`sushy-emulator --tapo --config=<config file>`

This will start the webserver in baremetal mode. If you want to deploy the service in a more
"production" environemnt, I've provided a docker image. Just set the environment variable: 

`SUSHY_EMULATOR_CONFIG=<path to config file>`

in your container, and you should have a working containerised deployment.

In the future, I will clean up the driver, and potentially support more baremetal interfaces if the need arises,
although this project was mostly done in order to support my home lab kubernetes deployment which can be seen: 

https://github.com/ashmantis1/edge-lab-infra


* Free software: Apache license
* Documentation: https://docs.openstack.org/sushy-tools
* Source: http://opendev.org/openstack/sushy-tools
* Bugs: https://storyboard.openstack.org/#!/project/openstack/sushy-tools
