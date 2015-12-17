#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Docker Monitoring
# Copyright (C) 2015 Crystone Sverige AB

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

import sys

try:
    import socket
except ImportError:
    print 'You must have the socket package available.'
    sys.exit(STATE_UNKNOWN)

try:
    import argparse
except ImportError:
    print 'You must have the argparse package installed.'
    sys.exit(STATE_UNKNOWN)

try:
    import docker
except ImportError:
    print 'You must have the docker-py package installed.'
    sys.exit(STATE_UNKNOWN)


parser = argparse.ArgumentParser(description='Check Docker')

parser.add_argument('--base', metavar='unix://var/run/docker.sock',
                    type=str, required=False,
                    default='unix://var/run/docker.sock',
                    help='Unix or TCP socket to Docker')
parser.add_argument('--container', metavar='name', type=str, required=False,
                    help='Name of container to check')
parser.add_argument('--health', action='store_true', required=False,
                    help='Do health check on container')
parser.add_argument('--warning', type=str, required=False,
                    help='Warning for containers if running summary')
parser.add_argument('--critical', type=str, required=False,
                    help='Critical for containers if running summary')

args = parser.parse_args()

try:
    client = docker.Client(base_url=args.base)
except Exception, e:
    print 'CRITICAL: Failed to create docker client: %s' % (e)
    sys.exit(STATE_CRITICAL)

docker_running = False

try:
    info = client.info()
    docker_running = True
except Exception, e:
    print 'CRITICAL: Docker is not running: %s' % (e)
    sys.exit(STATE_CRITICAL)

def check_port(port, host='127.0.0.1'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        s.close()
    except:
        return False

    return True

def do_summary(client, info):
    name = info['Name']
    version = info['ServerVersion']
    os = info['OperatingSystem']
    kernversion = info['KernelVersion']

    num_containers = info['Containers']
    num_images = info['Images'],
    num_routines = info['NGoroutines']
    num_fds = info['NFd']
    num_evlist = info['NEventsListener']

    FINAL_STATE = 'OK'
    FINAL_RETURN = 0

    print('%s: Docker %s on %s is running '
          '%s containers' % (FINAL_STATE, version, name, num_containers))
    sys.exit(FINAL_RETURN)

def get_container_by_name(client, name):
    if client is None:
        return False

    containers = client.containers(all=True)

    if containers is None:
        return False

    test_name = '/%s' % (name)

    for i in containers:
        if 'Names' not in i:
            continue

        for k in i['Names']:
            if k == test_name:
                return i

    return False

def check_container_status(status):
    if status is None or status == False:
        return False

    if 'Up' in status:
        return True

    return False

def is_ghost(status):
    if status is None or status == False:
        return False

    if 'Ghost' in status:
        return True

    return False

def do_container_check(client, name):
    container = get_container_by_name(client, name)

    if container is None or container == False:
        print 'CRITICAL: Failed to find container with name %s' % (name)
        sys.exit(STATE_CRITICAL)

    image = container['Image']
    status = container['Status']

    if is_ghost(status):
        print 'CRITICAL: Container %s is a ghost' % (name)
        sys.exit(STATE_CRITICAL)

    if check_container_status(status) == False:
        print 'CRITICAL: Container %s is not running' % (name)
        sys.exit(STATE_CRITICAL)

    if args.health == True:
        ports = container['Ports']

        ok_ports = []

        for p in ports:
            if 'PublicPort' not in p:
                continue

            ip = p['IP']

            if ip == '0.0.0.0':
                ip = '127.0.0.1'

            proto = p['Type']
            publicport = p['PublicPort']

            if proto not in ['tcp']:
                print 'CRITICAL: Does not support protocol %s' % (proto)
                sys.exit(STATE_CRITICAL)

            if check_port(publicport, ip) == False:
                print('CRITICAL: Container %s health check on public port '
                        '%s %s against %s failed' % (name, proto, publicport,
                            ip))
                sys.exit(STATE_CRITICAL)

            ok_ports.append(publicport)

        if len(ok_ports) <= 0:
            print('CRITICAL: Container %s health check passed but no ok ports'
                    ' was reported' % (name))

        ok_ports_string = str(ok_ports).strip('[]')

        print('OK: Container %s passed all health check on '
                'public ports %s' % (name, ok_ports_string))
        sys.exit(STATE_OK)
    
    print('OK: Container %s is running with image %s and status %s' % (name,
            image, status))
    sys.exit(STATE_OK)

if args.container != None:
    do_container_check(client, args.container)

do_summary(client, info)
