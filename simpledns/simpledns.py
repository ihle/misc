#!/usr/bin/env python
"""
Ben Ihle, 2010. Simple DNS server
for regex-based conditional domain
resolution and forwarding.
Place config (see below) into
~/dns.yml

Example config file: (note that [ip] is used indicate a nameserver)

    $ cat ~/dns.yml
    www.google.com: 123.34.45.56
    .*google.com: 127.0.0.1
    .*.mydomain.com: [10.0.0.1]
    default: [8.8.8.8, 'ns1.linode.com']

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
import dns.rdtypes
import dns.rdatatype
import SocketServer
import threading

class DNSProtocol(object):
    """
    Knows how to respond to DNS messages, but mostly by just shipping them off 
    to some real nameserver. The main entry point is `DNSProtocol.handle(data)`.
    """

    def __init__(self, config):
        self.config = config

    def handle(self, data):
        """ Handle a dns message. """
        msg = dns.message.from_wire(data) # XXX: handle exceptions!
        nameservers = self.config['default']
        if len(msg.question) > 1:
            # XXX: log warning
            print >>sys.stderr, "Warning: multi-question messages " +\
                    "are not yet supported. Using default nameserver"
            return dns.query.udp(msg, nameservers[0])
        question = msg.question[0]
        if question.rdtype == dns.rdatatype.A:
            ipaddr, nameservers = self.resolve_by_config(
                                          question.name.to_text(), self.config)
            if ipaddr is not None:
                return self.create_response(ipaddr, msg).to_wire()
        # let some nameserver handle the message
        # xxx: when do we use tcp? (response size-based?)
        return dns.query.udp(msg, nameservers[0]).to_wire()

    def resolve_by_config(self, name, config):
        """ 
        Look through `config` dictionary for either an IP address or a 
        nameserver to use to resolve a `name`. Returns 
        a tuple (`ipaddr`, [nameservers]) in which the `ipaddr` can be None
        but [nameservers] will always be non-empty.
        """
        nameservers = config['default']
        ipaddr = None
        for regex, item in config.iteritems():
            if regex != 'default' and re.search(regex, name):
                if isinstance(item, list):
                    nameservers = item
                    break
                elif isinstance(item, str):
                    ipaddr = item
                    break
        return ipaddr, nameservers

    def create_response(self, ipaddr, msg):
        """ 
        Create an response for an `A` message with an answer of `ipaddr` 
        """
        response = dns.message.make_response(msg)
        rrset = dns.rrset.RRset(msg.question[0].name, 1, 1)
        rrset.add(dns.rdtypes.IN.A.A(1, 1, ipaddr))
        response.answer.append(rrset)
        return response

class RequestHandler(SocketServer.BaseRequestHandler):
    """ does networking things. TODO: pre-parse config on server startup and 
        resolve any nameservers in config stored as names into IPs """

    def handle(self):
        data, sock = self.request
        config = yaml.load(file(os.path.expanduser("~/dns.yml"), 'r').read())
        protocol = DNSProtocol(config)
        sock.sendto(protocol.handle(data), self.client_address)

class Server(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass

if __name__ == '__main__':
    server = Server(("0.0.0.0", 53), RequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True) # daaaaayyyy-mon!
    server_thread.start()
    print "bdns Started."
    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        print "Closing..."
        server.shutdown()

