#!/usr/bin/env python

### Ben Ihle, 2010. Simple DNS server
### for regex-based conditional domain
### resolution and forwarding.
### Place config (see below) into
### ~/dns.yml

# dns query / response code shamelessly borrowed from: http://code.google.com/p/pymds/source/browse/trunk/pymds
# see also: http://www.dnspython.org/docs/1.9.4/html/
# and http://code.activestate.com/recipes/491264-mini-fake-dns-server/

# TODO: MX lookups etc...

# Example config file: (note that [] is used to indicate dns to forward request to)
#
#     $ cat ~/dns.yml
#     www.google.com: 123.34.45.56
#     .*google.com: 127.0.0.1
#     .*.mydomain.com: [10.0.0.1]
#     default: [8.8.8.8, 'ns1.linode.com']
#
# What this does
# ~~~~~~~~~~~~~~
# static mapping for www.google.com
# static mapping for .*google.com (e.g. mail.google.com, www.aaaddsssgoogle.com)
# forward *.mydomain.com to upstream 10.0.0.1 dns
# all other requests resolved via 8.8.8.8 and ns1.linode.com


import time
import socket
import yaml
import os
import re
import dns.resolver
import struct
import SocketServer
import threading

def format_response(qid, question, qtype, qclass, rcode, an_resource_records, ns_resource_records, ar_resource_records):
    resources = []
    resources.extend(an_resource_records)
    num_an_resources = len(an_resource_records)
    num_ns_resources = num_ar_resources = 0
    if rcode == 0:
        resources.extend(ns_resource_records)
        resources.extend(ar_resource_records)
        num_ns_resources = len(ns_resource_records)
        num_ar_resources = len(ar_resource_records)
    pkt = format_header(qid, rcode, num_an_resources, num_ns_resources, num_ar_resources)
    pkt += format_question(question, qtype, qclass)
    for resource in resources:
        pkt += format_resource(resource, question)
    return pkt

def format_header(qid, rcode, ancount, nscount, arcount):
    flags = 0
    flags |= (1 << 15)
    flags |= (1 << 10)
    flags |= (rcode & 0xf)
    hdr = struct.pack("!HHHHHH", qid, flags, 1, ancount, nscount, arcount)
    return hdr

def format_question(question, qtype, qclass):
    q = labels2str(question)
    q += struct.pack("!HH", qtype, qclass)
    return q


def format_resource(resource, question):
    r = ''
    r += labels2str(question)
    r += struct.pack("!HHIH", resource['qtype'], resource['qclass'], resource['ttl'], len(resource['rdata']))
    r += resource['rdata']
    return r

def parse_request(packet):
    hdr_len = 12
    header = packet[:hdr_len]
    qid, flags, qdcount, _, _, _ = struct.unpack('!HHHHHH', header)
    qr = (flags >> 15) & 0x1
    opcode = (flags >> 11) & 0xf
    rd = (flags >> 8) & 0x1
    #print "qid", qid, "qdcount", qdcount, "qr", qr, "opcode", opcode, "rd", rd
    if qr != 0 or opcode != 0 or qdcount == 0:
        raise DnsError("Invalid query")
    body = packet[hdr_len:]
    labels = []
    offset = 0
    while True:
        label_len, = struct.unpack('!B', body[offset:offset+1])
        offset += 1
        if label_len & 0xc0:
            raise DnsError("Invalid label length %d" % label_len)
        if label_len == 0:
            break
        label = body[offset:offset+label_len]
        offset += label_len
        labels.append(label)
    qtype, qclass= struct.unpack("!HH", body[offset:offset+4])
    if qclass != 1:
        raise DnsError("Invalid class: " + qclass)
    return (qid, labels, qtype, qclass)

def label2str(label):
    s = struct.pack("!B", len(label))
    s += label
    return s

def labels2str(labels):
    s = ''
    for label in labels:
        s += label2str(label)
    s += struct.pack("!B", 0)
    return s

def convert_to_ip(name, dns_to_use):
    """
        >>> convert_to_ip('66.102.11.104', ['8.8.8.8'])
        '66.102.11.104'
        >>> convert_to_ip('ns1.level3.net', ['8.8.8.8'])
        '209.244.0.1'
    """
    # resolve any names which are not dotted ips using the system dns
    try:
        socket.inet_aton(name)
        return name
    except Exception:
        pass

    try:
        r = dns.resolver.get_default_resolver()
        r.nameservers = dns_to_use
        return r.query(name)[0].to_text()
    except Exception as e:
        pass

    return name

def get_ip(domain, qtype, qclass, dns_config):
    """
        # must specify a default dns
        >>> get_ip('www.google.com', 1, 1, {})
        ('127.0.0.1', 'Error: no "default" dns value specified in the config, e.g. default: ["8.8.8.8"]. Returning localhost')

        # basic dns lookup using a real dns -- i.e. dns lookup for default
        >>> get_ip('ns1.level3.net', 1, 1, {'default': ['8.8.8.8']})
        ('209.244.0.1', "DNS ['8.8.8.8'] returned ip 209.244.0.1 for host ns1.level3.net")

        # use a static ip for the default (i.e. no dns)
        >>> get_ip('ns1.level3.net', 1, 1, {'default': '10.10.10.10'})
        ('10.10.10.10', 'Config matched ip 10.10.10.10 for host ns1.level3.net')

        # default + static override -- ensure the override works
        >>> get_ip('www.blah.com', 1, 1, {'default': '10.10.10.10', 'www.blah.com': '127.0.0.1'})
        ('127.0.0.1', 'Config matched ip 127.0.0.1 for host www.blah.com')

        # as above, but looking up something which will fall back on the default
        >>> get_ip('www.somethingelse.com', 1, 1, {'default': '10.10.10.10', 'www.blah.com': '127.0.0.1'})
        ('10.10.10.10', 'Config matched ip 10.10.10.10 for host www.somethingelse.com')

        # use a dns lookup for certain domains
        >>> get_ip('ns1.level3.net', 1, 1, {'default': '10.10.10.10', 'ns1.level3.net': ['8.8.8.8']})
        ('209.244.0.1', "DNS ['8.8.8.8'] returned ip 209.244.0.1 for host ns1.level3.net")

        # use a (hostname) dns lookup for certain domains
        >>> get_ip('www.level3.net', 1, 1, {'default': ['8.8.8.8'], 'www.level3.net': ['ns1.level3.net']})
        ('4.68.90.77', "DNS ['ns1.level3.net'] returned ip 4.68.90.77 for host www.level3.net")
    """
    # ensure we have a 'default' entry.
    if not dns_config.has_key('default'):
        stat = 'Error: no "default" dns value specified in the config, e.g. default: ["8.8.8.8"]. Returning localhost'
        return '127.0.0.1', stat
    # look at the regex lists for the first match
    ip_to_use = dns_config['default']
    for regex, dns_ip in dns_config.items():
        if regex is not 'default' and re.search(regex, domain):
            ip_to_use = dns_ip
            break

    if type(ip_to_use) == str:
        stat = 'Config matched ip %s for host %s' % (ip_to_use, domain)
        return ip_to_use, stat
    else:
        # do a look up using the dns servers specified (convert any host names to ips first) using the provided default server
        r = dns.resolver.get_default_resolver()
        r.nameservers = [convert_to_ip(name, dns_config['default']) for name in ip_to_use]
        try:
            answers = r.query(domain, rdtype=qtype, rdclass=qclass)
            for rdata in answers:
                ip = rdata.to_text()
                stat = 'DNS %s returned ip %s for host %s' % (ip_to_use, ip, domain)
                return ip, stat
        except Exception:
            stat = "%s couldn't resolve host %s" % (ip_to_use, domain)
            return False, stat

        # should never get here...
        return '127.0.0.1', stat

class DnsServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass

class DnsHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        cur_thread = threading.currentThread()

        start_time = time.time()

        data, sock = self.request
        dns_config = yaml.load(file(os.path.expanduser("~/dns.yml"), 'r').read())
        qid, domain, qtype, qclass = parse_request(data)
        ip, status = get_ip(".".join(domain), int(qtype), int(qclass), dns_config)

        print '[', time.strftime("%F %T"), ']:' , status, '(%03.1fms)' % ((time.time() - start_time) * 1000)
        if ip:
            status_code = 0
            ip_parts = ip.split(".")
            if reduce(lambda x, y: x and y.isdigit(), ip_parts): # Is the response an ip?
                # A / AAAA etc?
                rdata = str.join('',map(lambda x: chr(int(x)), ip_parts))
            else:
                # PTR (reverse dns)?
                rdata = str.join('', map(lambda x: label2str(x), ip_parts))
            # TODO: actually return a the correct response for the different request types. Esp. MX
            r = [{
                    'rdata': rdata,
                    'qclass': int(qclass),
                    'qtype': int(qtype),
                    'ttl': 10 # Not too short, but still pretty short. Could screw with DNS prefetch in your browser of choice...
                }]
        else:
            status_code = 3
            r = []
        resp = format_response(qid, domain, qtype, qclass, status_code, r, [], [])
        sock.sendto(resp, self.client_address)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    server = DnsServer(("0.0.0.0", 53), DnsHandler)
    server_thread = threading.Thread(target=server.serve_forever)

    # Pron. "deemon".
    server_thread.setDaemon(True)
    server_thread.start()

    print '[', time.strftime("%F %T"), ']:' , "DNS server started."

    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        print '[', time.strftime("%F %T"), ']:' , "Closing..."
        server.shutdown()

