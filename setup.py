from setuptools import find_packages, setup

setup(
    name="ciftag",
    description="ciftag module",
    author="sjh",
    version="0.1.1",
    packages=find_packages(include=['ciftag']),
    scripts=['ciftag/bin/ciftag'],
    include_package_data=True,
)
