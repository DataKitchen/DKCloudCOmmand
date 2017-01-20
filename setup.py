from distutils.core import setup
from setuptools import find_packages
import os

# http://stackoverflow.com/questions/7719380/python-setup-py-sdist-error-operation-not-permitted
if os.environ.get('USER', '') == 'vagrant':
    del os.link
"""

When you update the requirments.txt, delete the local DKCloudCommand.egg-info directory (if you have one)

# Goal:
pip install DKCloudCommand
# for testing:
pip install -i https://testpypi.python.org/pypi DKCloudCommand

# undo / cleanup / uninstall
pip uninstall DKCloudCommand

# PyPi getting started
# http://peterdowns.com/posts/first-time-with-pypi.html

# TO UPDATE THE DOWNLOADABLE VERSION ----- BEGIN -----

# Prerequisite:  Create a .pypirc per above

# VERSION UPDATE:
# 1) update the version string in 3 places in this file
# 2) update version in __main__.py

export comment="misc bugs related to merging and file updates"
git add .
git commit -m "${comment}"
git push
git tag '1.0.4' -m "$comment"
git push --tags origin master

# PRODUCTION
# if prompted for a username check with the team for the credentials.
python setup.py register -r pypi # register
python setup.py sdist upload -r pypi  # upload
git describe # show latest tag, FYI

# TO UPDATE THE DOWNLOADABLE VERSION ----- END -----

# TEST
#python setup.py register -r pypitest
#python setup.py sdist upload -r pypitest
python setup.py register -r pypitest sdist upload -r pypitest # all in one
git describe # show latest tag

# how to create an executable in the right place:
# https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/

# More Info:
#  http://www.siafoo.net/article/77
#  https://pythonhosted.org/setuptools/setuptools.html
#  http://stackoverflow.com/questions/14399534/how-can-i-reference-requirements-txt-for-the-install-requires-kwarg-in-setuptool
"""

## DEBUG START
# print '%%% starting setup'
# cwd = os.getcwd()
# print 'in setup in', cwd
# print 'files'
# for root, subdirs, files in os.walk(cwd):
#     print root
#     print os.listdir(root)

## DEBUG END

#  Remember, this code is run on the developer machine and then it is run on the target install machine

try1 = 'requirements.txt'
try2 = 'DKCloudCommand.egg-info/requires.txt'

if os.path.exists(try1):  # if developer environment
    reqts = try1
elif os.path.exists(try2):  # target machine
    reqts = try2
else:
    print 'cannot fine list of requirements'
    exit(2)
    
with open(reqts) as f:
    listOrequirements = f.read().splitlines()

# print 'List of requirements'
# print listOrequirements

setup(
        name='DKCloudCommand',
        packages=find_packages(),
        entry_points={
            'console_scripts': [
                'dk = DKCloudCommand.cli.__main__:main'
            ]
        },
        install_requires=listOrequirements,
        # the following is what find_packages() currently returns:
        # packages=['DKCloudCommand', 'DKCloudCommand.cli', 'DKCloudCommand.modules', 'DKCloudCommand.tests'],
        version='1.0.10',
        description='DataKitchen Cloud Command Line',
        author='DataKitchen',
        author_email='info@datakitchen.io',
        url='https://github.com/DataKitchen/DKCloudCommand',
        download_url='https://github.com/DataKitchen/DKCloudCommand/tarball/1.0.10',
        keywords=['DataKitchen', 'Cloud', 'Commandline', 'Analytics', 'Agile Data'],
        classifiers=[]
)

# print '%%% finishing setup'
