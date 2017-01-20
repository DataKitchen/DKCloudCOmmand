import requests
import urllib
from distutils.util import strtobool

import time
from requests import RequestException
from DKCloudCommandConfig import DKCloudCommandConfig
from DKRecipeDisk import *
from DKReturnCode import *

__author__ = 'DataKitchen, Inc.'

"""
NOMENCLATURE

Some example files:

abspath
  /tmp/test/simple/description.json
  /tmp/test/simple/resources/cools.sql

Here are what the parts are called:

file_name
    description.json
    cools.sql

recipe_name
  simple

filepath # as known to the user
api_file_key # specifies the file to create/update/delete
             # relative to being in the top recipe directory
             # i.e. file name and path to the file name, relative to the recipe root
             # recipe root = cd /tmp/test/simple
  resources/cool.sql
  cool.sql

recipe_file_key # used as a key to the dictionary
  simple/resources # for cool.sql
  simple # for description.json

recipe_file # location on disk including the recipe name
  simple/resources/cool.sql
  simple/description.json

filedir # the directory portion between the recipe and the file_name
  resources


For the CLI, assume the user has CD to the top of the recipe
e.g.
  cd /var/tmp/test/simple

"""


class DKCloudAPI(object):
    _use_https = False
    _auth_token = None
    DKAPP_KITCHEN_FILE = 'kitchen.json'
    DKAPP_KITCHENS_DIR = 'kitchens'
    MESSAGE = 'message'
    FILEPATH = 'filepath'
    FILE = 'file'
    FILENAME = 'filename'
    JSON = 'json'
    TEXT = 'text'
    SHA = 'sha'
    LAST_UPDATE_TIME = 'last_update_time'

    # helpers ---------------------------------

    def __init__(self, dk_cli_config):
        if isinstance(dk_cli_config, DKCloudCommandConfig) is True:
            self._config = dk_cli_config
            self._auth_token = None

    def get_config(self):
        return self._config

    @staticmethod
    def _get_json(response):
        if response is None or response.text is None:
            return None
        rvd = response.text
        try:
            resp = json.loads(json.loads(rvd))
        except (ValueError, KeyError, Exception):
            try:
                rvd2 = rvd.replace("\\n","\n").replace("\\", "").replace("\"{", "{").replace("}\"", "}")
                resp = json.loads(rvd2)
            except Exception:
                # self.assertTrue(False, 'unable to get resp json loads: %s \n response = (%s)' % (str(v), str(rv)))
                resp = None
        return resp

    @staticmethod
    def _get_json_new(response):
        if response is None or response.text is None:
            return None
        rvd = response.text
        rvd2 = rvd.replace("\\", "").replace("\"{", "{").replace("}\"", "}").replace('\\"', '"')
        try:
            resp = json.loads(json.loads(rvd2))
        except (ValueError, KeyError, Exception), v:
            try:
                # rvd2 = rvd.replace("\\", "").replace("\"{", "{").replace("}\"", "}")
                rvd2 = rvd.replace("\\", "").replace("\"{", "{").replace("}\"", "}").replace('\\"', '"')
                # sed -e 's/\\//' -e 's/"\"{"/"{"/' -e 's/"}\""/"}"/' -e 's/\\"/"/'
                resp = json.loads(rvd2)
            except Exception:
                # self.assertTrue(False, 'unable to get resp json loads: %s \n response = (%s)' % (str(v), str(rv)))
                resp = None
        return resp

    @staticmethod
    def _valid_response(response):
        if response is None:
            return False
        if response.status_code == 200 or response.status_code == 201:
            return True
        else:
            return False

    def get_url_for_direct_rest_call(self):
        if self._use_https is False:
            return '%s:%s' % (self._config.get_ip(), self._config.get_port())
        else:
            return "must use http"

    def login(self, force_login=True):
        if force_login is True or self._auth_token is None:
            self._auth_token = self._get_token()
        return self._auth_token

    def _get_common_headers(self, one_time_token=None):
        if one_time_token is not None:
            return {'Authorization': 'Bearer %s' % one_time_token}
        else:
            return {'Authorization': 'Bearer %s' % self._auth_token}

    def _is_token_valid(self, token):
        url = '%s/v2/validatetoken' % (self.get_url_for_direct_rest_call())
        try:
            response = requests.get(url, headers=self._get_common_headers(token))
        except (RequestException, ValueError, TypeError), c:
            print "validatetoken: exception: %s" % str(c)
            return False
        if response is None:
            print "validatetoken failed. No response."
            return False
        elif response.status_code != 200:
            print 'validatetoken failed: status_code - %d, reason - %s' % (response.status_code, response.reason)
            return False

        if response.text is not None and len(response.text) > 1:
            if strtobool(response.text.strip().lower()):
                return True
            else:
                return False
        else:
            print 'validatetoken failed: token status unknown'
            return False

    def _login(self):
        credentials = dict()
        credentials['username'] = self._config.get_username()
        credentials['password'] = self._config.get_password()
        url = '%s/v2/login' % (self.get_url_for_direct_rest_call())
        try:
            response = requests.post(url, data=credentials)
        except (RequestException, ValueError, TypeError), c:
            print "login: exception: %s" % str(c)
            return None
        if DKCloudAPI._valid_response(response) is False:
            return None

        if response is not None:
            if response.text is not None and len(response.text) > 10:
                if response.text[0] == '"':
                    jwt = response.text.replace('"', '').strip()
                else:
                    jwt = response.text
                self._config.set_jwt(jwt)
                self._config.save_to_stored_file_location()
                return jwt
            else:
                print 'Invalid jwt token returned from server'
                return None
        else:
            print 'login: error logging in'
            return None

    def _get_token(self):
        # Javascript Web Tokens, handle all the
        # timeouts and whatnot that are required.
        # We can check the time out locally, but it is better
        # to have our server do it to ensure that the jwt hasn't
        # been tampered with.
        jwt = self._config.get_jwt()
        if jwt is not None:
            if self._is_token_valid(jwt):
                self._config.set_jwt(jwt)
                self._config.save_to_stored_file_location()
                return jwt
            else:
                pass
                # print 'Stored token is invalid. Logging in with stored credentials.'
        jwt = self._login()
        if jwt is not None:
            self._config.set_jwt(jwt)
            self._config.save_to_stored_file_location()
            return jwt
        else:
            return None

    # implementation ---------------------------------
    @staticmethod
    def rude():
        return '**rude**'

    # It looks like this is only called from TestCloudAPI.py.  Consider moving this function
    # return kitchen dict
    def get_kitchen_dict(self, kitchen_name):
        rv = self.list_kitchen()
        if rv.ok():
            kitchens = rv.get_payload()
        if kitchens is None:
            return None
        for kitchen in kitchens:
            if isinstance(kitchen, dict) is True and 'name' in kitchen and kitchen_name == kitchen['name']:
                return kitchen
        return None

    # returns a list of kitchens
    # '/v2/kitchen/list', methods=['GET'])
    def list_kitchen(self):
        rc = DKReturnCode()
        url = '%s/v2/kitchen/list' % (self.get_url_for_direct_rest_call())
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            rc.set(rc.DK_FAIL, 'list_kitchen: exception: %s' % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict['kitchens'])
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def secret_list(self,path):
        rc = DKReturnCode()
        path = path or ''
        url = '%s/v2/secret/%s' % (self.get_url_for_direct_rest_call(), path)
        try:
            start_time = time.time()
            response = requests.get(url, headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'secret_list - elapsed: %d' % elapsed_recipe_status
            rdict = self._get_json(response)
            if DKCloudAPI._valid_response(response):
                rc.set(rc.DK_SUCCESS, None, rdict['value'])
            else:
                arc = DKAPIReturnCode(rdict, response)
                rc.set(rc.DK_FAIL, arc.get_message())
            return rc
        except (RequestException, ValueError, TypeError), c:
            s = "secrent_list: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

    def secret_exists(self,path):
        rc = DKReturnCode()
        path = path or ''
        url = '%s/v2/secret/check/%s' % (self.get_url_for_direct_rest_call(), path)
        try:
            start_time = time.time()
            response = requests.get(url, headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'secret_exists - elapsed: %d' % elapsed_recipe_status
            rdict = self._get_json(response)
            if DKCloudAPI._valid_response(response):
                rc.set(rc.DK_SUCCESS, None, rdict['value'])
            else:
                arc = DKAPIReturnCode(rdict, response)
                rc.set(rc.DK_FAIL, arc.get_message())
            return rc
        except (RequestException, ValueError, TypeError), c:
            s = "secrent_list: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

    def secret_write(self,path,value):
        rc = DKReturnCode()
        path = path or ''
        url = '%s/v2/secret/%s' % (self.get_url_for_direct_rest_call(), path)
        try:
            start_time = time.time()
            pdict = {'value':value}
            response = requests.post(url, data=json.dumps(pdict), headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'secret_write - elapsed: %d' % elapsed_recipe_status
            rdict = self._get_json(response)
            if DKCloudAPI._valid_response(response):
                rc.set(rc.DK_SUCCESS, None, None)
            else:
                arc = DKAPIReturnCode(rdict, response)
                rc.set(rc.DK_FAIL, arc.get_message())
            return rc
        except (RequestException, ValueError, TypeError), c:
            s = "secret_write: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

    def secret_delete(self,path):
        rc = DKReturnCode()
        path = path or ''
        url = '%s/v2/secret/%s' % (self.get_url_for_direct_rest_call(), path)
        try:
            start_time = time.time()
            response = requests.delete(url, headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'secret_write - elapsed: %d' % elapsed_recipe_status
            rdict = self._get_json(response)
            if DKCloudAPI._valid_response(response):
                rc.set(rc.DK_SUCCESS, None, None)
            else:
                arc = DKAPIReturnCode(rdict, response)
                rc.set(rc.DK_FAIL, arc.get_message())
            return rc
        except (RequestException, ValueError, TypeError), c:
            s = "secret_delete: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc


    # '/v2/kitchen/update/<string:kitchenname>', methods=['POST'])
    def update_kitchen(self, update_kitchen, message):
        if update_kitchen is None:
            return False
        if isinstance(update_kitchen, dict) is False or 'name' not in update_kitchen:
            return False
        if message is None or isinstance(message, basestring) is False:
            message = 'update_kitchens'
        pdict = dict()
        pdict[DKCloudAPI.DKAPP_KITCHEN_FILE] = update_kitchen
        pdict[DKCloudAPI.MESSAGE] = message
        url = '%s/v2/kitchen/update/%s' % (self.get_url_for_direct_rest_call(), update_kitchen['name'])
        try:
            response = requests.post(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            print "update_kitchens: exception: %s" % str(c)
            return None
        if DKCloudAPI._valid_response(response) is True and rdict is not None and isinstance(rdict, dict) is True:
            return True
        else:
            return False

    # '/v2/kitchen/create/<string:existingkitchenname>/<string:newkitchenname>', methods=['GET'])
    def create_kitchen(self, existing_kitchen_name, new_kitchen_name, message):
        rc = DKReturnCode()
        if existing_kitchen_name is None or new_kitchen_name is None:
            rc.set(rc.DK_FAIL, 'Need to supply an existing kitchen name')
            return rc
        if isinstance(existing_kitchen_name, basestring) is False or isinstance(new_kitchen_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'Kitchen name needs to be a string')
            return rc
        if message is None or isinstance(message, basestring) is False:
            message = 'update_kitchens'
        pdict = dict()
        pdict[DKCloudAPI.MESSAGE] = message
        url = '%s/v2/kitchen/create/%s/%s' % (self.get_url_for_direct_rest_call(),
                                              existing_kitchen_name, new_kitchen_name)
        try:
            response = requests.get(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            rc.set(rc.DK_FAIL, 'create_kitchens: exception: %s' % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # '/v2/kitchen/delete/<string:existingkitchenname>', methods=['DELETE'])
    def delete_kitchen(self, existing_kitchen_name, message):
        rc = DKReturnCode()
        if existing_kitchen_name is None:
            rc.set(rc.DK_FAIL, 'Need to supply an existing kitchen name')
            return rc
        if isinstance(existing_kitchen_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'Kitchen name needs to be a string')
            return rc
        if message is None or isinstance(message, basestring) is False:
            message = 'delete_kitchen'
        pdict = dict()
        pdict[DKCloudAPI.MESSAGE] = message
        url = '%s/v2/kitchen/delete/%s' % (self.get_url_for_direct_rest_call(), existing_kitchen_name)
        try:
            response = requests.delete(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            rc.set(rc.DK_FAIL, 'delete_kitchens: exception: %s' % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    def modify_kitchen_settings(self, kitchen_name, add=(), unset=()):
        rc = self.get_kitchen_settings(kitchen_name)
        if not rc.ok():
            return rc

        kitchen_json = rc.get_payload()
        overrides = kitchen_json['recipeoverrides']

        msg = ''
        commit_message = ''

        if len(add) > 0:
            for add_this in add:
                matches = [existing_override for existing_override in overrides if existing_override['variable'] == add_this[0]]
                if len(matches) == 0:
                    overrides.append({'variable': add_this[0], 'value': add_this[1], 'category':'from_command_line'})
                else:
                    matches[0]['value'] = add_this[1]

                msg += "{} added with value '{}'\n".format(add_this[0], add_this[1])
                if len(commit_message) != 0:
                    commit_message += " ; {} added".format(add_this[0])
                else:
                    commit_message += "{} added".format(add_this[0])

        # tom_index = next(index for (index, d) in enumerate(lst) if d["name"] == "Tom")
        # might be a string?
        if len(unset) > 0:
            if isinstance(unset, list) or isinstance(unset, tuple):
                for unset_this in unset:
                    match_index = next((index for (index, d) in enumerate(overrides) if d["variable"] == unset_this), None)
                    if match_index is not None:
                        del overrides[match_index]
                        msg += "{} unset".format(unset_this)
                        if len(commit_message) != 0:
                            commit_message += " ; {} unset".format(unset_this)
                        else:
                            commit_message += "{} unset".format(unset_this)
            else:
                match_index = next((index for (index, d) in enumerate(overrides) if d["variable"] == unset), None)
                if match_index is not None:
                    del overrides[match_index]
                    msg += "{} unset".format(unset)
                    if len(commit_message) != 0:
                        commit_message += " ; {} unset".format(unset)
                    else:
                        commit_message += "{} unset".format(unset)

        rc = self.put_kitchen_settings(kitchen_name, kitchen_json, commit_message)
        if not rc.ok():
            return rc

        rc = DKReturnCode()
        rc.set(rc.DK_SUCCESS, msg, overrides)
        return rc

    def get_kitchen_settings(self, kitchen_name):
        rc = DKReturnCode()
        url = '%s/v2/kitchen/settings/%s' % (self.get_url_for_direct_rest_call(), kitchen_name)
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError) as c:
            rc.set(rc.DK_FAIL, 'settings_kitchen: exception: %s' % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    def put_kitchen_settings(self, kitchen_name, kitchen_dict, msg):
        rc = DKReturnCode()

        try:
            kitchen_json = json.dumps(kitchen_dict)
        except ValueError as ve:
            # Make sure this is valid json
            rc.set(rc.DK_FAIL, ve.message)
            return rc

        d1 = dict()
        d1['kitchen.json'] = kitchen_dict
        d1['message'] = msg
        url = '%s/v2/kitchen/settings/%s' % (self.get_url_for_direct_rest_call(), kitchen_name)
        try:
            response = requests.put(url, headers=self._get_common_headers(), data=json.dumps(d1))
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError) as c:
            rc.set(rc.DK_FAIL, 'settings_kitchen: exception: %s' % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # returns a list of recipes
    def list_recipe(self, kitchen):
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        url = '%s/v2/kitchen/recipenames/%s' % (self.get_url_for_direct_rest_call(), kitchen)
        try:
            start_time = time.time()
            response = requests.get(url, headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'list_recipe - elapsed: %d' % elapsed_recipe_status

            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "list_recipe: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict['recipes'])
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # returns a list of recipes
    def recipe_create(self, kitchen, name):
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        url = '%s/v2/recipe/create/%s/%s' % (self.get_url_for_direct_rest_call(), kitchen,name)
        try:
            start_time = time.time()
            response = requests.post(url, headers=self._get_common_headers())
            elapsed_recipe_status = time.time() - start_time
            print 'list_recipe - elapsed: %d' % elapsed_recipe_status

            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "list_recipe: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # returns a recipe
    # api.add_resource(GetRecipeV2, '/v2/recipe/get/<string:kitchenname>/<string:recipename>',
    #             methods=['GET', 'POST'])
    # get() gets all files in a recipe
    # post() gets a list of files in a recipe in the post as a 'recipe-files' list of dir / file names
    def get_recipe(self, kitchen, recipe, list_of_files=None):
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        url = '%s/v2/recipe/get/%s/%s' % (self.get_url_for_direct_rest_call(),
                                          kitchen, recipe)
        try:
            if list_of_files is not None:
                params = dict()
                params['recipe-files'] = list_of_files
                response = requests.post(url, data=json.dumps(params), headers=self._get_common_headers())
            else:
                response = requests.post(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "get_recipe: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            if recipe not in rdict['recipes']:
                rc.set(rc.DK_FAIL, None, "Unable to find recipe %s" % recipe)
            else:
                rc.set(rc.DK_SUCCESS, None, rdict)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def update_file(self, kitchen, recipe, message, api_file_key, file_contents):
        """
        returns success or failure (True or False)
        '/v2/recipe/update/<string:kitchenname>/<string:recipename>', methods=['POST']
        :param self: DKCloudAPI
        :param kitchen: basestring
        :param recipe: basestring  -- kitchen name, basestring
        :param message: basestring message -- commit message, basestring
        :param api_file_key:  -- the recipe based file path (recipe_name/node1/data_sources, e.g.)
        :param file_contents: -- character string of the recipe file to update

        :rtype: boolean
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        if api_file_key is None or isinstance(api_file_key, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with api_file_key parameter')
            return rc
        if file_contents is None or isinstance(file_contents, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with file_contents parameter')
            return rc
        pdict = dict()
        pdict[self.MESSAGE] = message
        pdict[self.FILEPATH] = api_file_key
        pdict[self.FILE] = file_contents
        url = '%s/v2/recipe/update/%s/%s' % (self.get_url_for_direct_rest_call(),
                                             kitchen, recipe)
        try:
            response = requests.post(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "update_file: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # Create a file in a recipe
    def add_file(self, kitchen, recipe, message, api_file_key, file_contents):
        """
        returns True for success or False for failure
        '/v2/recipe/create/<string:kitchenname>/<string:recipename>', methods=['PUT']
        :param self: DKCloudAPI
        :param kitchen: basestring
        :param recipe: basestring  -- kitchen name, basestring
        :param message: basestring message -- commit message, basestring
        :param api_file_key:  -- file name and path to the file name, relative to the recipe root
        :param file_contents: -- character string of the recipe file to update

        :rtype: boolean
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        if api_file_key is None or isinstance(api_file_key, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with api_file_key parameter')
            return rc
        if file_contents is None or isinstance(file_contents, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with file_contents parameter')
            return rc
        pdict = dict()
        pdict[self.MESSAGE] = message
        pdict[self.FILEPATH] = api_file_key
        pdict[self.FILE] = file_contents
        url = '%s/v2/recipe/create/%s/%s' % (self.get_url_for_direct_rest_call(), kitchen, recipe)
        try:
            response = requests.put(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "add_file: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # api.add_resource(DeleteRecipeFileV2, '/v2/recipe/delete/<string:kitchenname>/<string:recipename>',
    #              methods=['DELETE'])
    def delete_file(self, kitchen, recipe, message, recipe_file_key, recipe_file):
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        if recipe_file_key is None or isinstance(recipe_file_key, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe_file_key parameter')
            return rc
        if recipe_file is None or isinstance(recipe_file, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe_file parameter')
            return rc
        pdict = dict()
        pdict[self.MESSAGE] = message
        pdict[self.FILEPATH] = recipe_file_key
        pdict[self.FILE] = recipe_file
        url = '%s/v2/recipe/delete/%s/%s' % (self.get_url_for_direct_rest_call(),
                                             kitchen, recipe)
        try:
            response = requests.delete(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "delete_file: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    def get_compiled_serving(self, kitchen, recipe_name, variation_name):
        """
        get the compiled version of arecipe with variables applied for a specific variation in a kitchen
        returns a dictionary
        '/v2/servings/compiled/get/<string:kitchenname>/<string:recipename>/<string:variationname>', methods=['GET']
        :param self: DKCloudAPI
        :param kitchen: basestring
        :param recipe_name: basestring  -- kitchen name, basestring
        :param variation_name: basestring message -- name of variation, basestring
        :rtype: dict
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen')
            return rc
        if recipe_name is None or isinstance(recipe_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe_name')
            return rc
        if variation_name is None or isinstance(variation_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with variation_name')
            return rc
        url = '%s/v2/servings/compiled/get/%s/%s/%s' % (self.get_url_for_direct_rest_call(),
                                                        kitchen, recipe_name, variation_name)
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            rc.set(rc.DK_FAIL, "get_compiled_serving: exception: %s" % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict[rdict.keys()[0]])
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def merge_kitchens_improved(self, from_kitchen, to_kitchen, resolved_conflicts=None):
        """
        merges kitchens
        '/v2/kitchen/merge/<string:kitchenname>/<string:kitchenname>', methods=['POST']
        :param resolved_conflicts:
        :param self: DKCloudAPI
        :param from_kitchen: string
        :param to_kitchen: string
        :rtype: dict
        """
        rc = DKReturnCode()
        if from_kitchen is None or isinstance(from_kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with from kitchen')
            return rc
        if to_kitchen is None or isinstance(to_kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with to kitchen')
            return rc
        url = '%s/v2/kitchen/merge/%s/%s' % (self.get_url_for_direct_rest_call(), from_kitchen, to_kitchen)
        try:
            if resolved_conflicts is not None and len(resolved_conflicts) > 0:
                data = dict()
                data['resolved_conflicts'] = resolved_conflicts
                response = requests.post(url, data=json.dumps(data), headers=self._get_common_headers())
            else:
                response = requests.post(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            rc.set("merge_kitchens: exception: %s" % str(c))
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def merge_file(self, kitchen, recipe, file_path, file_contents, orig_head, last_file_sha):
        """
        Returns the result of merging a local file with the latest version on the remote.
        This does not cause any side-effects on the server, and no actual merge is performed in the remote repo.
        /v2/file/merge/<string:kitchenname>/<string:recipename>/<path:filepath>, methods=['POST']
        :param kitchen: name of the kitchen where this file lives
        :param recipe: name of the recipe that owns this file
        :param file_path: path to the file, relative to the recipe
        :param file_contents: contents of the file
        :param orig_head: sha of commit head of the branch when this file was obtained.
        :param last_file_sha: The sha of the file when it was obtained from the server.
        :return: dict
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False or \
                recipe is None or isinstance(recipe, basestring) is False or \
                file_path is None or isinstance(file_path, basestring) is False or \
                orig_head is None or isinstance(orig_head, basestring) is False or \
                last_file_sha is None or isinstance(last_file_sha, basestring) is False or \
                file_contents is None:
            rc.set(rc.DK_FAIL, 'One or more parameters is invalid. ')
            return rc

        params = dict()
        params['orig_head'] = orig_head
        params['last_file_sha'] = last_file_sha
        params['content'] = file_contents
        adjusted_file_path = file_path
        url = '%s/v2/file/merge/%s/%s/%s' % (self.get_url_for_direct_rest_call(), kitchen, recipe, adjusted_file_path)
        try:
            response = requests.post(url, data=json.dumps(params), headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError, TypeError), c:
            print "merge_file: exception: %s" % str(c)
            return None
        if DKCloudAPI._valid_response(response) is True and rdict is not None and isinstance(rdict, dict) is True:
            rc.set(rc.DK_SUCCESS, None, rdict)
            return rc
        else:
            rc.set(rc.DK_FAIL, str(rdict))
            return rc

    # returns a recipe
    def recipe_status(self, kitchen, recipe, local_dir=None):
        """
        gets the status of a recipe
        :param self: DKCloudAPI
        :param kitchen: string
        :param recipe: string
        :param local_dir: string --
        :rtype: dict
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        url = '%s/v2/recipe/tree/%s/%s' % (self.get_url_for_direct_rest_call(),
                                           kitchen, recipe)
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "get_recipe: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            # Now get the local sha.
            if local_dir is None:
                check_path = os.getcwd()
            else:
                if os.path.isdir(local_dir) is False:
                    print 'Local path %s does not exist' % local_dir
                    return None
                else:
                    check_path = local_dir
            local_sha = get_directory_sha(check_path)
            remote_sha = rdict['recipes'][recipe]
            rv = compare_sha(remote_sha, local_sha)
            rc.set(rc.DK_SUCCESS, None, rv)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # returns a recipe
    def recipe_tree(self, kitchen, recipe):
        """
        gets the status of a recipe
        :param self: DKCloudAPI
        :param kitchen: string
        :param recipe: string
        :rtype: dict
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc
        if recipe is None or isinstance(recipe, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe parameter')
            return rc
        url = '%s/v2/recipe/tree/%s/%s' % (self.get_url_for_direct_rest_call(),
                                           kitchen, recipe)
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "recipe_tree: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            remote_sha = rdict['recipes'][recipe]
            rc.set(rc.DK_SUCCESS, None, remote_sha)
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
        return rc

    # --------------------------------------------------------------------------------------------------------------------
    #  Order commands
    # --------------------------------------------------------------------------------------------------------------------
    #  Cook a recipe varation in a kitchen
    def create_order(self, kitchen, recipe_name, variation_name, node_name=None):
        """
        Full graph
        '/v2/order/create/<string:kitchenname>/<string:recipename>/<string:variationname>',
            methods=['PUT']

        Single node
        '/v2/order/create/onenode/<string:kitchenname>/<string:recipename>/<string:variationname>/<string:nodename',
            methods=['PUT']

        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen')
            return rc
        if recipe_name is None or isinstance(recipe_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with recipe_name')
            return rc
        if variation_name is None or isinstance(variation_name, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with variation_name')
            return rc

        if node_name is None:
            url = '%s/v2/order/create/%s/%s/%s' % (self.get_url_for_direct_rest_call(),
                                                   kitchen, recipe_name, variation_name)
        else:
            url = '%s/v2/order/create/onenode/%s/%s/%s/%s' % (self.get_url_for_direct_rest_call(),
                                                              kitchen, recipe_name, variation_name, node_name)

        try:
            response = requests.put(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError), c:
            s = "create_order: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict['serving_chronos_id'])
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def order_resume(self, orderrun_id):

        rc = DKReturnCode()
        #if kitchen is None or isinstance(kitchen, basestring) is False:
        #    rc.set(rc.DK_FAIL, 'issue with kitchen')
        #    return rc
        #if recipe_name is None or isinstance(recipe_name, basestring) is False:
        #    rc.set(rc.DK_FAIL, 'issue with recipe_name')
        #    return rc
        #if variation_name is None or isinstance(variation_name, basestring) is False:
        #    rc.set(rc.DK_FAIL, 'issue with variation_name')
        #    return rc
        if orderrun_id is None or isinstance(orderrun_id, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with orderrun_id')
            return rc

        orderrun_id2 = urllib.quote(orderrun_id)

        url = '%s/v2/order/resume/%s' % (self.get_url_for_direct_rest_call(), orderrun_id2)
        try:
            response = requests.put(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError), c:
            s = "orderrun_delete: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, rdict['serving_chronos_id'])
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    # Get the details about a Order-Run (fka Serving)
    def orderrun_detail(self, kitchen, pdict, return_all_data=False):
        """
        api.add_resource(OrderDetailsV2, '/v2/order/details/<string:kitchenname>', methods=['POST'])
        :param self: DKCloudAPI
        :param kitchen: string
        :param pdict: dict
        :param return_all_data: boolean
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen')
            return rc
        url = '%s/v2/order/details/%s' % (self.get_url_for_direct_rest_call(),
                                          kitchen)
        try:
            response = requests.post(url, data=json.dumps(pdict), headers=self._get_common_headers())
            rdict = self._get_json(response)
            if False:
                import pickle
                pickle.dump(rdict, open("files/orderrun_detail.p", "wb"))
            pass
        except (RequestException, ValueError), c:
            s = "orderrun_detail: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

        if DKCloudAPI._valid_response(response):
            if return_all_data is False:
                rc.set(rc.DK_SUCCESS, None, rdict['servings'])
            else:
                rc.set(rc.DK_SUCCESS, None, rdict)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def list_order(self, kitchen, save_to_file=None):
        """
        List the orders for a kitchen or recipe
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen parameter')
            return rc

        url = '%s/v2/order/status/%s' % (self.get_url_for_direct_rest_call(), kitchen)
        try:
            response = requests.get(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            pass
        except (RequestException, ValueError, TypeError), c:
            s = "get_recipe: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if not DKCloudAPI._valid_response(response):
            arc = DKAPIReturnCode(rdict)
            rc.set(rc.DK_FAIL, arc.get_message())
        else:
            if save_to_file is not None:
                import pickle
                pickle.dump(rdict, open(save_to_file, "wb"))

            rc.set(rc.DK_SUCCESS, None, rdict)
        return rc

    def order_delete_all(self, kitchen):
        """
        api.add_resource(OrderDeleteAllV2, '/v2/order/deleteall/<string:kitchenname>', methods=['DELETE'])
        :param self: DKCloudAPI
        :param kitchen: string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if kitchen is None or isinstance(kitchen, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with kitchen')
            return rc
        url = '%s/v2/order/deleteall/%s' % (self.get_url_for_direct_rest_call(),
                                            kitchen)
        try:
            response = requests.delete(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError), c:
            s = "order_delete_all: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, None)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def order_delete_one(self, order_id):
        """
        api.add_resource(OrderDeleteV2, '/v2/order/delete/<string:orderid>', methods=['DELETE'])
        :param self: DKCloudAPI
        :param order_id: string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if order_id is None or isinstance(order_id, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with order_id')
            return rc
        order_id2 = urllib.quote(order_id)
        url = '%s/v2/order/delete/%s' % (self.get_url_for_direct_rest_call(),
                                         order_id2)
        try:
            response = requests.delete(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError), c:
            s = "order_delete_one: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, None)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    # Get the details about a Order-Run (fka Serving)
    def delete_orderrun(self, orderrun_id):
        """
        api.add_resource(ServingDeleteV2, '/v2/serving/delete/<string:servingid>', methods=['DELETE'])
        :param self: DKCloudAPI
        :param orderrun_id: string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if orderrun_id is None or isinstance(orderrun_id, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with orderrun_id')
            return rc
        orderrun_id2 = urllib.quote(orderrun_id)
        url = '%s/v2/serving/delete/%s' % (self.get_url_for_direct_rest_call(), orderrun_id2)
        try:
            response = requests.delete(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
            if DKCloudAPI._valid_response(response):
                rc.set(rc.DK_SUCCESS, None, None)
                return rc
            else:
                arc = DKAPIReturnCode(rdict, response)
                rc.set(rc.DK_FAIL, arc.get_message())
                return rc
        except (RequestException, ValueError), c:
            s = "orderrun_delete: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

    
    def order_stop(self, order_id):
        """
        api.add_resource(OrderStopV2, '/v2/order/stop/<string:orderid>', methods=['PUT'])
        :param self: DKCloudAPI
        :param order_id: string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if order_id is None or isinstance(order_id, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with order_id')
            return rc
        order_id2 = urllib.quote(order_id)
        url = '%s/v2/order/stop/%s' % (self.get_url_for_direct_rest_call(),
                                       order_id2)
        try:
            response = requests.put(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError), c:
            s = "order_stop: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc

        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, None)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc

    def orderrun_stop(self, orderrun_id):
        """
        api.add_resource(ServingStopV2, '/v2/serving/stop/<string:servingid>', methods=['Put'])
        :param self: DKCloudAPI
        :param orderrun_id: string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if orderrun_id is None or isinstance(orderrun_id, basestring) is False:
            rc.set(rc.DK_FAIL, 'issue with orderrun_id')
            return rc
        orderrun_id2 = urllib.quote(orderrun_id)
        url = '%s/v2/serving/stop/%s' % (self.get_url_for_direct_rest_call(),
                                         orderrun_id2)
        try:
            response = requests.put(url, headers=self._get_common_headers())
            rdict = self._get_json(response)
        except (RequestException, ValueError), c:
            s = "order_stop: exception: %s" % str(c)
            rc.set(rc.DK_FAIL, s)
            return rc
        if DKCloudAPI._valid_response(response):
            rc.set(rc.DK_SUCCESS, None, None)
            return rc
        else:
            arc = DKAPIReturnCode(rdict, response)
            rc.set(rc.DK_FAIL, arc.get_message())
            return rc
