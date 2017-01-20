import unittest
from sys import path
import json
import os, tempfile
import uuid
from DKCommonUnitTestSettings import DKCommonUnitTestSettings
from DKActiveServingWatcher import DKActiveServingWatcherSingleton

#if '../../' not in path:
#    path.insert(0, '../../')

from DKCloudAPI import DKCloudAPI
from DKCloudAPIMock import DKCloudAPIMock
from DKCloudCommandConfig import DKCloudCommandConfig
import tempfile
from server.dkapp import main
from multiprocessing import Process
import netifaces
import time

__author__ = 'DataKitchen, Inc.'

def get_ip_address():
    ifces = [ifce for ifce in netifaces.interfaces() if ifce.startswith('eth')]
    ifce = ifces[-1]
    return netifaces.ifaddresses(ifce)[netifaces.AF_INET][0]['addr']

IP_ADDRESS = get_ip_address()
MESOS_URL = "http://%s:5050" % IP_ADDRESS
CHRONOS_URL = "http://%s:4400" % IP_ADDRESS


class BaseTestCloud(DKCommonUnitTestSettings):

    _cr_config = DKCloudCommandConfig()

    # cr_config_dict = dict()
    _branch = 'kitchens-plus'
    _api = None
    _use_mock = True
    _start_dir = None  # the tests change directories so save the starting point

    def startup_server(self):
        if os.environ.get('DKCLI_CONFIG_LOCATION') is not None:
            config_file_location = os.path.expandvars('${DKCLI_CONFIG_LOCATION}').strip()
        else:
            config_file_location = "../DKCloudCommandConfig.json"
        # get the connection info
        config = DKCloudCommandConfig()
        config.init_from_file(config_file_location)
        config.delete_jwt()
        config.save_to_stored_file_location()


        app_config = {
            "mesos-url": MESOS_URL,
            "chronos-url": CHRONOS_URL,
            "generic-run-script": "https://s3.amazonaws.com/mesos-scripts/generic_run_recipe_v2.sh",
            "github-customer": "DKCustomers",
            "working-dir" : "work",
            "port-number": "14001"
        }
        server_config = None
        with tempfile.NamedTemporaryFile(delete=False, dir='./') as temp:
            temp.write(json.dumps(app_config))
            server_config = temp.name
            temp.flush()

        self.server_thread = Process(target=main, args=(None, server_config, False))
        self.server_thread.start()

        time.sleep(3)

    def setUp(self):
        print '%s.%s - setUp' % (self.__class__.__name__,self._testMethodName)
        self.startup_server()

        self._start_dir = os.getcwd()  # save directory

        if os.environ.get('DKCLI_CONFIG_LOCATION') is not None:
            config_file_location = os.path.expandvars('${DKCLI_CONFIG_LOCATION}').strip()
        else:
            config_file_location = "../DKCloudCommandConfig.json"
        # get the connection info
        self.assertTrue(self._cr_config.init_from_file(config_file_location))

        try:
            use_mock = os.path.expandvars('${USE_MOCK}').strip()
        except Exception:
            use_mock = None

        if use_mock == 'True':
            self._use_mock = True
        else:
            self._use_mock = False

        if self._use_mock is True:
            self._api = DKCloudAPIMock(self._cr_config)
        else:
            self._api = DKCloudAPI(self._cr_config)

        # connect / authenticate
        self.assertIsNotNone(self._api.login())

    def tearDown(self):
        os.chdir(self._start_dir)  # restore directory
        # In case test_active_serving_watcher fails
        DKActiveServingWatcherSingleton().stop_watcher()
        self.server_thread.terminate()

    # helpers ---------------------------------
    def _make_kitchen_dir(self, kitchen_name, change_dir=True):
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=self._TEMPFILE_LOCATION)
        kitchen_dir = os.path.join(temp_dir, kitchen_name)
        os.mkdir(kitchen_dir)
        if change_dir:
            os.chdir(kitchen_dir)
        plug_dir = os.path.join(kitchen_dir, '.dk')
        os.mkdir(plug_dir)
        with open(os.path.join(plug_dir, 'KITCHEN_META'), 'w') as kitchen_file:
            kitchen_file.write(kitchen_name)
        os.mkdir(os.path.join(plug_dir, 'recipes'))
        return temp_dir, kitchen_dir

    def _make_recipe_dir(self, recipe_name, kitchen_name, change_dir=True):
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir)
        recipes_meta_dir = os.path.join(os.path.join(kitchen_dir, '.dk'), 'recipes')
        recipe_meta_dir = os.path.join(recipes_meta_dir, recipe_name)
        os.makedirs(recipe_meta_dir)
        with open(os.path.join(recipe_meta_dir, 'RECIPE_META'), 'w') as recipe_file:
            recipe_file.write(recipe_name)
        recipe_dir = os.path.join(temp_dir, kitchen_name, recipe_name)
        os.mkdir(recipe_name)
        if change_dir:
            os.chdir(recipe_dir)
        return temp_dir, kitchen_dir, recipe_dir

    @staticmethod
    def _get_unit_test_guid():
        file_name = 'my_unitest_guid.txt'
        if os.path.isfile(file_name):
            with open('my_unitest_guid.txt', 'r') as f:
                myguid = f.read()
            f.closed
            return myguid
        else:
            newguid = str(uuid.uuid4())[:8]
            with open(file_name, 'w') as f:
                f.write(newguid)
            f.closed
            return newguid

    def _add_my_guid(self, base_branch):
        return base_branch + '_ut_' + self._get_unit_test_guid()

    def _get_run_variation(self):
        if 'cloud.datakitchen.io' in self._cr_config.get_ip():
            variation_name = 'variation-test-production05'
            print 'Running production recipe.'
        else:
            variation_name = 'variation-test'
        return variation_name

    def _get_run_variation_for_recipe(self, recipe_name, repeater=False):
        if recipe_name == 'parallel-recipe-test':
            if 'cloud.datakitchen.io' in self._cr_config.get_ip():
                if repeater is True:
                    variation_name = 'variation-test-production05-repeat'
                else:
                    variation_name = 'variation-test-production05-now'
                print 'Running production recipe.'
            else:
                if repeater is True:
                    variation_name = 'variation-test-repeat'
                else:
                    variation_name = 'variation-test'
            return variation_name
        elif recipe_name == 'simple':
            if 'cloud.datakitchen.io' in self._cr_config.get_ip():
                variation_name = 'simple-variation-now'
                print 'Running production recipe.'
            else:
                variation_name = 'simple-variation-now-vagrant'
            return variation_name
        elif recipe_name == 'test-everything-recipe':
            if 'cloud.datakitchen.io' in self._cr_config.get_ip():
                variation_name = 'variation-morning-prod05'
                print 'Running production recipe.'
            else:
                variation_name = 'variation-morning-vagrant'
            return variation_name

    def _get_the_dict(self, t):
        self.assertIsNotNone(t)
        self.assertTrue(isinstance(t, basestring))
        try:
            rd = json.loads(t)
        except ValueError:
            rd = None
            self.assertTrue(False)
        return rd

    def _get_the_json_str(self, d):
        self.assertIsNotNone(d)
        self.assertTrue(isinstance(d, dict))
        try:
            rs = json.dumps(d, indent=4)
        except ValueError:
            rs = None
            self.assertTrue(False)
        return rs
