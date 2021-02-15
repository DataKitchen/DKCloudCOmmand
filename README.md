# DKCloudCommand
[![PyPI version](https://badge.fury.io/py/DKCloudCommand.svg)](https://badge.fury.io/py/DKCloudCommand)

**DKCloudCommand** is the command line interface for interacting with [DataKitchen's](https://datakitchen.io/dk/) DataOps platform.  The companion web application is available [here](https://cloud.datakitchen.io/dk/#/welcome).

# DataOps

### Seven Steps to DataOps

1. Add Data And Logic Tests
2. Put All Steps To Version Control
3. Branch & Merge
4. Use Multiple Environments
5. Reuse & Containerize
6. Parameterize Your Processing
7. Work Without Fear

### DataOps Resources
 
* [DataOps Manifesto](http://dataopsmanifesto.org/)
* [The DataOps Blog](https://medium.com/data-ops)
* [@DataKitchen_io](https://twitter.com/datakitchen_io)


# Requirements

### Python

DKCloudCommand requires [Python 3.x](https://www.python.org/downloads/release/python-380/).

Python 3 users can use DKCloudCommand in their preferred virtual environment manager:

* [venv](https://docs.python.org/3/library/venv.html)
* [conda](https://conda.io/docs/)

### Python Packages

[Python package requirements](https://github.com/DataKitchen/DKCloudCommand/blob/master/requirements.txt) will be installed or updated when installing DKCloudCommand.

* [aniso8601](https://pypi.python.org/pypi/aniso8601)
* [Jinja2==2.7.3](http://jinja.pocoo.org/)
* [MarkupSafe==0.23](https://pypi.python.org/pypi/MarkupSafe)
* [nose==1.3.7](http://nose.readthedocs.io/en/latest/)
* [pytz==2015.4](http://pytz.sourceforge.net/)
* [requests==2.8.1](http://docs.python-requests.org/en/master/)
* [six==1.10.0](https://pypi.python.org/pypi/six)
* [websocket-client==0.32.0](https://pypi.python.org/pypi/websocket-client)
* [Werkzeug==0.10.4](https://pypi.python.org/pypi/Werkzeug)
* [click==6.2](https://pypi.python.org/pypi/click)
* [pyopenssl](https://pypi.python.org/pypi/pyOpenSSL)
* [PyJWT](https://pypi.python.org/pypi/PyJWT)
* [prettytable](https://pypi.python.org/pypi/PrettyTable)

# Installation

To install DKCloudCommand:

`$ pip install DKCloudCommand`

# Upgrading

Determine the currently installed version:

`$ dk --version`

To upgrade DKCloudCommand:

`$ pip install DKCloudCommand --upgrade`

# Documentation

Detailed documentation is available [here](https://docs.datakitchen.io/articles/datakitchen-help/dkcloudcommand).

