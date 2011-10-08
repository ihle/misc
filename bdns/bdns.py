#!/usr/bin/env python
"""
Jay Sweeney, Ben Ihle, 2011.
Simple DNS server
for regex-based conditional domain
resolution and forwarding.
Place config (see below) into
./bdns_settings.py

What this does
~~~~~~~~~~~~~~
static mapping for www.google.com
static mapping for .*google.com (e.g. mail.google.com, www.aaaddsssgoogle.com)
forward *.mydomain.com to upstream 10.0.0.1 dns
all other requests resolved via 8.8.8.8 and ns1.linode.com
"""
import sys
import time
import os
import re
import dns.resolver
import dns.message
import dns.rdtypes.IN.A
import dns.rdatatype
import SocketServer
from SocketServer import ThreadingMixIn, UDPServer
import socket
import logging
import imp

logging.basicConfig(
    format='[%(asctime)s] %(levelname)-10s %(message)s', 
    datefmt='%d/%m/%Y %I:%M:%S %p',
    level=logging.INFO)
log = logging.getLogger(__name__)

class DNSProtocol(object):
    """
    Knows how to respond to DNS messages, but mostly by just shipping them off 
    to some real nameserver. The main entry point is `DNSProtocol.handle(data)`.
    """
    def __init__(self, config):
        self.config = config

    def handle(self, data):
        """ Handle a dns message. """
        with open('request.bin', 'wb') as fout:
            fout.write(data)
        msg = dns.message.from_wire(data)
        log.debug('[REQUEST]\n%s\n[/REQUEST]', str(msg))
        nameservers = self.config.default
        if len(msg.question) > 1:
            log.warning("Warning: multi-question messages " +\
                    "are not yet supported. Using default nameserver.")
            return self.forward_request(msg, nameservers).to_wire()
        question = msg.question[0]
        log.info('%-10s%-8s%s', 'Question:', msg.id, str(question))
        if question.rdtype == dns.rdatatype.A:
            name = question.name.to_text()
            ipaddr, nameservers = self.resolve_by_config(name)
            if ipaddr:
                response = self.create_response(ipaddr, msg)
                log.info('%-10s%-8s%s DNS: %s', 'Answer:', response.id, map(str, response.answer), '[* STATIC IP *]')
                with open('response.bin', 'wb') as fout:
                    fout.write(response.to_wire())
                return response.to_wire()

        # let some nameserver handle the message
        response = self.forward_request(msg, nameservers)
        log.debug('[RESPONSE]\n%s\n[/RESPONSE]', str(response))
        log.info('%-10s%-8s%s DNS: %r', 'Answer:', response.id, map(str, response.answer), nameservers)
        return response.to_wire()


    def forward_request(self, msg, nameservers):
        for ns in nameservers:
            try:
                # xxx: when do we use tcp? (message size-based?)
                response = dns.query.udp(msg, ns, timeout=10)
                return response
            except:
                continue
        # XXX: raise exception here, or return some sort of 
        # error response to client

    def resolve_by_config(self, name):
        """ 
        Look through `config` dictionary for either an IP address or a 
        nameserver to use to resolve a `name`. Returns 
        a tuple (ipaddr, [nameservers]) in which the `ipaddr` can be None
        but [nameservers] will always be non-empty.
        """
        # remove trailing '.' from name, if present.
        if name[-1] is '.':
            name = name[:-1]

        nameservers = self.config.default
        ipaddr = None
        for key, item in self.config.hosts.iteritems():
            # TODO: hosts really should be ordered so that you can effectively override.
            if (key == name) or (hasattr(key, 'search') and key.search(name)):
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
        rrset.ttl = 5
        rrset.add(dns.rdtypes.IN.A.A(1, 1, ipaddr))
        response.answer.append(rrset)
        return response

class RequestHandler(SocketServer.BaseRequestHandler):
    """ handles requests and does some bad non-threadsafe config reloading """
    def handle(self):
        data, sock = self.request
        self.server.config = getconfig() # XXX: race here!
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
    """ Read and validate config. Also resolve any nameserver names 
    TODO: log info on resolving dnses """

    try:
        fp, path, desc = imp.find_module('bdns_settings')
        try:
            bdns_settings = imp.load_module('bdns_settings', fp, path, desc)
        finally:
            if fp:
                fp.close()
    except ImportError:
        log.error("Could not load bdns_settings.py. Using defaults.")
        return {'default': '8.8.8.8'}

    try:
        default_nameservers = bdns_settings.default
    except KeyError:
        raise ConfigException('No "default" found in bdns_settings.py')
    for ns in default_nameservers:
        if not isip(ns):
            raise ConfigException("Bad default nameserver IP: `%s`" % ns)
    for key, value in bdns_settings.hosts.iteritems():
        if isinstance(value, list): # nameserver
            for thing in value:
                if not isip(thing):
                    resolver = dns.resolver.get_default_resolver()
                    resolver.nameservers = default_nameservers
                    try:
                        answer = resolver.query(thing)
                        bdns_settings.hosts[key] = [answer[0].address]
                    except:
                        raise ConfigException("`%s` does not look like "
                                "an ipv4 address and does not resolve "
                                "using the default nameservers" % thing)
        else: # should be a valid ip
            if not isip(value):
                raise ConfigException("`%s` is not a valid "
                                      "ipv4 address" % value)
    return bdns_settings

if __name__ == '__main__':
    server = Server(("0.0.0.0", 53), RequestHandler, getconfig())
    try: 
        server.serve_forever()
    except KeyboardInterrupt:
        print "Shutting down..."
        server.server_close()

