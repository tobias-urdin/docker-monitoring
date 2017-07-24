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
parser.add_argument('--blacklist', type=str, required=False,
                    help='Blacklist ports to check', nargs='*')

args = parser.parse_args()

try:
    client = docker.Client(base_url=args.base, version='1.19')
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

def do_summary(client, info, warn=None, crit=None):
    name = info['Name']
    num_containers = info['Containers']

    if crit is not None:
        if int(num_containers) <= int(crit):
            print('CRITICAL: Docker on %s is running but we could '
                    'only find %s containers which is below critical '
                    'threshold of %s' % (name, num_containers, crit))
            sys.exit(STATE_CRITICAL)

    if warn is not None:
        if int(num_containers) <= int(warn):
            print('WARNING: Docker on %s is running but we could '
                    'only find %s containers which is below warning '
                    'threshold of %s' % (name, num_containers, warn))
            sys.exit(STATE_WARNING)

    FINAL_STATE = 'OK'
    FINAL_RETURN = 0

    print('%s: Docker on %s is running '
          '%s containers' % (FINAL_STATE, name, num_containers))
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
            if 'PublicPort' not in p and 'PrivatePort' not in p:
                continue

            if 'IP' in p:
                ip = p['IP']

                if ip == '0.0.0.0':
                    ip = '127.0.0.1'
            else:
                ip = '127.0.0.1'

            proto = p['Type']

            if 'PublicPort' in p:
                port = p['PublicPort']
            elif 'PrivatePort' in p:
                port = p['PrivatePort']
            else:
                continue

            if args.blacklist is not None:
                if str(port) in args.blacklist:
                    continue

            if proto not in ['tcp']:
                print 'CRITICAL: Does not support protocol %s' % (proto)
                sys.exit(STATE_CRITICAL)

            if check_port(port, ip) == False:
                print('CRITICAL: Container %s health check on port '
                        '%s %s against %s failed' % (name, proto, port,
                            ip))
                sys.exit(STATE_CRITICAL)

            ok_ports.append(port)

        if len(ok_ports) <= 0:
            print('CRITICAL: Container %s health check passed but no OK ports'
                    ' were reported' % (name))
            sys.exit(STATE_CRITICAL)

        ok_ports_string = str(ok_ports).strip('[]')

        print('OK: Container %s passed all health check on '
                'ports %s' % (name, ok_ports_string))
        sys.exit(STATE_OK)
    
    print('OK: Container %s is running with image %s and status %s' % (name,
            image, status))
    sys.exit(STATE_OK)

if args.container != None:
    do_container_check(client, args.container)

do_summary(client, info, args.warning, args.critical)
