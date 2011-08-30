from setuptools import setup

setup(
	name='simpledns',
	version='0.0001',
	description='The Ihle DNS',
	author='Ben Ihle',
	author_email='ben@not.tell.ing',
	url='https://github.com/ihle/misc',
	scripts=['simpledns/simpledns.py'],
	install_requires=['dnspython', 'pyyaml']
)