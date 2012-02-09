
from distutils.core import setup

setup(
    name='python-graphite',
    version='0.2.0',
    author='Ronan Klyne',
    author_email='python-graphite@rklyne.net',
    packages=['graphite'],
    package_data={
        'graphite': [
            'config.ini',
            '*.txt',
            'Jena-2.6.4/*.txt',
            'Jena-2.6.4/*.html',
            'Jena-2.6.4/lib/*.jar',
        ],
    },
    scripts=[],
    url='http://code.google.com/p/python-graphite/',
    license='LICENSE.txt',
    description='A flexible RDF hacking library built on JPype and Jena',
    long_description=open('README.txt').read(),
)
