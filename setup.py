from setuptools import setup, find_packages
import os
import ast


def get_version_from_init():
    """Obtain library version from main init."""
    init_file = os.path.join(
        os.path.dirname(__file__), 'dataclasses_hierarchy', '__init__.py'
    )
    with open(init_file) as fd:
        for line in fd:
            if line.startswith('__version__'):
                return ast.literal_eval(line.split('=', 1)[1].strip())


with open('README.md') as f:
    readme = f.read()

with open('COPYING') as f:
    lic = f.read()


setup(
    name='dataclasses_hierarchy',
    version=get_version_from_init(),
    description='Dataclasses-hierarchy: hierarchies and chained initalization for dataclasses',
    long_description=readme,
    author='Cédric Hernaslteens',
    author_email='cedric.hernalsteens@ulb.be',
    url='https://github.com/ulb-metronu/dataclasses-hierarchy',
    license=lic,
    packages=find_packages(exclude=('tests', 'docs', 'examples')),
    install_requires=[],
    package_data={'dataclasses-hierarchy': []},
)
