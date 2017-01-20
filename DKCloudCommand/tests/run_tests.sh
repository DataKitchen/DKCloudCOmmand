#!/bin/bash

#CONFIG=" { \"dk-cloud-file-location\": \"/home/ubuntu/DKCloudCommand/DKCloudCommand/DKCloudCommandConfig.json\", \"dk-cloud-ip\": \"http://localhost\", \"dk-cloud-password\": \"cccccccc\", \"dk-cloud-port\": \"14001\", \"dk-cloud-username\": \"unittests@datakitchen.io\" }"
#echo $CONFIG > ../DKCloudCommandConfig.json

coverage run -p -m unittest discover . -p 'Test*.py'
