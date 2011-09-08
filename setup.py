from setuptools import setup

setup(
	name='bdns',
	version='0.0001',
	description="Ben's DNS",
	author='Ben Ihle',
	author_email='ben@not.tell.ing',
	url='https://github.com/ihle/misc',
	scripts=['bdns/bdns.py'],
	install_requires=['dnspython', 'pyyaml']
)