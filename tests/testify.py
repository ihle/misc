import unittest
from simpledns import convert_to_ip, get_ip

class TestConverToIP(unittest.TestCase):
	def test_convert_to_ip(self):
		ip = convert_to_ip('66.102.11.104', ['8.8.8.8'])
		self.assertEquals(ip, '66.102.11.104')
		ip = convert_to_ip('ns1.level3.net', ['8.8.8.8'])
        self.assertTrue(ip, '209.244.0.1')

class TestGetIP(unittest.TestCase):
    def test_default_dns_check(self):
    	""" must specify a default dns """
        result = get_ip('www.google.com', 1, 1, {})
        self.assertEqual(result, 
        	('127.0.0.1', 'Error: no "default" dns value specified' 
        				  ' in the config, e.g. default: ["8.8.8.8"]. '
        				  'Returning localhost'))
        				  
	def test_lookup_on_default_dns(self):
		"""basic dns lookup using a real dns -- i.e. dns lookup for default"""
        result = get_ip('ns1.level3.net', 1, 1, {'default': ['8.8.8.8']})
        self.assertEqual(result, 
        	('209.244.0.1', "DNS ['8.8.8.8'] returned ip 209.244.0.1 "
        					"for host ns1.level3.net")

    def test_lookup_with_static_default_ip(self):
	    """use a static ip for the default (i.e. no dns)"""
        result = get_ip('ns1.level3.net', 1, 1, {'default': '10.10.10.10'})
        self.assertEqual(result, 
        	('10.10.10.10', 'Config matched ip 10.10.10.10 '
        					'for host ns1.level3.net')
	
	def test_static_override(self):
        """default + static override -- ensure the override works"""
        result = get_ip('www.blah.com', 1, 1, 
        			{'default': '10.10.10.10', 'www.blah.com': '127.0.0.1'})
       	self.assertEqual(result, ('127.0.0.1', 'Config matched ip 127.0.0.1 '
       										   'for host www.blah.com')

    def test_fall_back_to_default(self):
        """
        as above, but looking up something which will fall back on the default
        """
		res = get_ip('www.somethingelse.com', 1, 1, 
				{'default': '10.10.10.10', 'www.blah.com': '127.0.0.1'})
        self.assertEqual(res, ('10.10.10.10', 'Config matched ip 10.10.10.10 '
        									  'for host www.somethingelse.com')

    def test_override_lookup(self):
	    """use a (hostname) dns lookup for certain domains"""
        result = get_ip('www.level3.net', 1, 1, 
        		{'default': ['8.8.8.8'], 'www.level3.net': ['ns1.level3.net']})
        self.assertEqual('4.68.90.77', 
     		"DNS ['ns1.level3.net'] returned ip "
     		"4.68.90.77 for host www.level3.net")

	def test_reverse_override_lookup(self):
        """use a dns lookup for certain domains"""
        result = get_ip('ns1.level3.net', 1, 1, 
        		{'default': '10.10.10.10', 'ns1.level3.net': ['8.8.8.8']})
        self.assertEqual(result, ('209.244.0.1', 
        		"DNS ['8.8.8.8'] returned ip 209.244.0.1 "
        		"for host ns1.level3.net")
