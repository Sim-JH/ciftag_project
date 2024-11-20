from setuptools import find_packages, setup
from version import version

setup(
    name="ciftag",
    description="ciftag module",
    author="sjh",
    version=version,
    packages=find_packages(include=['ciftag']),
    scripts=['ciftag/bin/ciftag'],
    include_package_data=True,
)
