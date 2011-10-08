default = ['192.168.0.1']

import re
hosts = {
    # exact name match, resolve to static ip
    'www.something.com': '10.51.12.34',

    # exact name match, resolve using nameservers (8.8.8.8, and 8.8.4.4)
    'www.google.com': ['8.8.8.8', '8.8.4.4'],

    # regular expression matching
    re.compile('.*\.somethingelse\.com'): '127.0.0.1',
}

# something a little more dynamic...
import random
rand = random.randrange(2,255)
random_ip = '127.0.0.%d' % (rand)
hosts['funky.thing'] = random_ip

# $ nslookup www.something.com 127.0.0.1
# ... Address: 10.51.12.34

# $ nslookup www.google.com 127.0.0.1
# ... Address: 74.125.237.83

# $ nslookup blah.somethingelse.com 127.0.0.1
# ... Address: 127.0.0.2

# $ nslookup funky.thing 127.0.0.1
# ... Address: 127.0.0.27

# $ nslookup funky.thing 127.0.0.1
# ... Address: 127.0.0.38

