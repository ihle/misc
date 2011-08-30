from setuptools import setup

setup(
	name='simple_dns',
	version='0.0001',
	description='The Ihle DNS',
	author='Ben Ihle',
	author_email='ben@not.tell.ing',
	url='https://github.com/ihle/misc',
	scripts=['simple_dns.py'],
	install_requires=['dnspython', 'pyyaml']
)