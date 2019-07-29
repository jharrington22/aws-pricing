import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "aws_audit",
    version = "0.0.1",
    author = "Shruti Jain",
    author_email = "shrjain@redhat.com",
    description = ("A script to audit AWS resources and total spending"),
    license = "Apache License 2.0",
    keywords = "aws audit",
    url = "https://github.com/openshift/aws-pricing/",
    packages=['aws_audit'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: AWS Pricing",
        "License :: OSI Approved :: Apache License 2.0",
    ],
)
