#!/usr/bin/env python
"""
Jay Sweeney, Ben Ihle, 2011.
Simple DNS server
for regex-based conditional domain
resolution and forwarding.
Place config (see below) into
~/dns.yml

Example config file: (note that [ip] is used indicate a nameserver)

    $ cat ~/dns.yml
    www.google.com: 123.34.45.56
    .*google.com: 127.0.0.1
    .*.mydomain.com: [10.0.0.1]
    default: [8.8.8.8, ns1.linode.com]

What this does
~~~~~~~~~~~~~~
static mapping for www.google.com
static mapping for .*google.com (e.g. mail.google.com, www.aaaddsssgoogle.com)
forward *.mydomain.com to upstream 10.0.0.1 dns
all other requests resolved via 8.8.8.8 and ns1.linode.com
"""
import sys
import time
import yaml
import os
import re
import dns.resolver
import dns.message
import dns.rdtypes.IN.A
import dns.rdatatype
import SocketServer
from SocketServer import ThreadingMixIn, UDPServer
import threading
import socket

CONFIGPATH = os.path.expanduser("~/dns.yml")

class DNSProtocol(object):
    """
    Knows how to respond to DNS messages, but mostly by just shipping them off 
    to some real nameserver. The main entry point is `DNSProtocol.handle(data)`.
    """
    def __init__(self, config):
        self.config = config

    def handle(self, data):
        """ Handle a dns message. """
        msg = dns.message.from_wire(data)
        nameservers = self.config['default']
        if len(msg.question) > 1:
            # XXX: log warning
            print >>sys.stderr, "Warning: multi-question messages " +\
                    "are not yet supported. Using default nameserver."
            return dns.query.udp(msg, nameservers[0]).to_wire()
        question = msg.question[0]
        if question.rdtype == dns.rdatatype.A:
            name = question.name.to_text()
            ipaddr, nameservers = self.resolve_by_config(name)
            if ipaddr:
                return self.create_response(ipaddr, msg).to_wire()
        # let some nameserver handle the message
        # xxx: when do we use tcp? (message size-based?)
        result = dns.query.udp(msg, nameservers[0]).to_wire()
        return result

    def resolve_by_config(self, name):
        """ 
        Look through `config` dictionary for either an IP address or a 
        nameserver to use to resolve a `name`. Returns 
        a tuple (ipaddr, [nameservers]) in which the `ipaddr` can be None
        but [nameservers] will always be non-empty.
        """
        nameservers = self.config['default']
        ipaddr = None
        for regex, item in self.config.iteritems():
            if regex != 'default' and re.search(regex, name):
                if isinstance(item, list):
                    nameservers = item
                else:
                    ipaddr = item
                break
        return ipaddr, nameservers

    def create_response(self, ipaddr, msg):
        """ 
        Create a response for an `A` message with an answer of `ipaddr` 
        """
        response = dns.message.make_response(msg)
        rrset = dns.rrset.RRset(msg.question[0].name, 1, 1)
        rrset.add(dns.rdtypes.IN.A.A(1, 1, ipaddr))
        response.answer.append(rrset)
        return response

class RequestHandler(SocketServer.BaseRequestHandler):
    """ handles requests and does some bad non-threadsafe config reloading """
    def handle(self):
        data, sock = self.request
        self.server.config = reloadconfig(self.server.config) # XXX: race here!
        protocol = DNSProtocol(self.server.config)
        sock.sendto(protocol.handle(data), self.client_address)

class Server(ThreadingMixIn, UDPServer):
    def __init__(self, server_address, RequestHandlerClass, config):
        self.config = config
        UDPServer.__init__(self, server_address, RequestHandlerClass)

class ConfigException(Exception): 
    pass

def isip(s):
    try:
        socket.inet_aton(s)
        return True
    except socket.error:
        return False

def getconfig():
    """ Read and validate config. Also resolve any nameserver names """
    config = yaml.load(open(CONFIGPATH))
    try:
        default_nameservers = config['default']
    except KeyError:
        raise ConfigException('No default nameservers found in config')
    for ns in default_nameservers:
        if not isip(ns):
            raise ConfigException("Bad default nameserver IP: `%s`" % ns)
    for key, value in config.iteritems():
        if isinstance(value, list): # nameserver
            for thing in value:
                if not isip(thing):
                    resolver = dns.resolver.get_default_resolver()
                    resolver.nameservers = default_nameservers
                    try:
                        answer = resolver.query(thing)
                        config[key] = [answer[0].address]
                    except:
                        raise ConfigException("`%s` does not look like "
                                "an ipv4 address and does not resolve "
                                "using the default nameservers" % thing)
        else: # should be a valid ip
            if not isip(value):
                raise ConfigException("`%s` is not a valid "
                                      "ipv4 address" % value)
    config['__mtime'] = os.stat(CONFIGPATH).st_mtime
    return config

def reloadconfig(oldconfig):
    """ reload config if it has changed since last load """
    config = oldconfig
    if os.stat(CONFIGPATH).st_mtime > oldconfig['__mtime']:
        try:
            config = getconfig()
            print "Config reloaded."
        except ConfigException as e:
            print >>sys.stderr, "bnds config has errors, not loading it: %s" % e
    return config

if __name__ == '__main__':
    server = Server(("0.0.0.0", 53), RequestHandler, getconfig())
    try: 
        server.serve_forever()
    except KeyboardInterrupt:
        print "Shutting down..."
        server.shutdown()

