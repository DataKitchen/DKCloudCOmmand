import re

__author__ = 'DataKitchen, Inc.'
import unittest
import os
import shutil
import tempfile
import datetime
import time
from sys import path
from subprocess import check_output
from click.testing import CliRunner
from BaseTestCloud import BaseTestCloud

if not '../modules/' in path:
    path.insert(0, '../modules/')
from DKKitchenDisk import DKKitchenDisk
from my_test_kitchen_list_by_exec_command import *

if '../cli/' not in path:
    path.insert(0, '../cli/')
from dk import dk


class TestCommandLine(BaseTestCloud):
    _TEMPFILE_LOCATION = '/var/tmp'

    #
    # def test_orderrun_detail_bad_variation_tmp_gil(self):
    #     kitchen = 'shadow0325'
    #     runner = CliRunner()
    #     result = runner.invoke(dk, ['orderrun-info',
    #                                 '--kitchen', kitchen])
    #     self.assertTrue(0 == result.exit_code)

    # def test_quick(self):
    #     working_dir = "/Users/eric/dev/DKCloudCommand/DKCloudCommand/tests/examples/CovanceHighwayTest/covance_highway"
    #     # working_dir = "/Users/eric/dev/DKCloudCommand/DKCloudCommand/tests/examples/dev0701bstrx/cg-development"
    #     os.chdir(working_dir)
    #     runner = CliRunner()
    #     # result = runner.invoke(dk, ["km", '-s', 'CovanceHighwayTest', '-t', 'CovanceHighwayTemp'])
    #     result = runner.invoke(dk, ["km", '-s', 'ece_child', '-t', 'ece_parent'])
    #     # result = runner.invoke(dk, ["fr", "resources/raw_covance_highway.sql"])
    #     # result = runner.invoke(dk, ["fu", "-m", "this is a developer comment", "resources/redshift/additive_weeks/unload_sw_rbd_product_oldest.sql"])
    #     rv = result.output

    def test_alias(self):
        runner = CliRunner()
        # result = runner.invoke(dk, ["rs"])
        result = runner.invoke(dk, ["aliases"])
        rv = result.output
        self.assertTrue('kc - kitchen-create' in rv)
        self.assertTrue('ord - orderrun-delete' in rv)

        result = runner.invoke(dk, ["kl"])
        rv = result.output
        self.assertTrue('CLI-Top' in rv)

    def test_kitchen_config(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["kitchen-config", "--list"])
        rv = result.output

    def test_a_kitchen_list_by_exec(self):
        # This unit test now assumes that you have a virtualenvironment named
        # DKCloudCommand
        tv1 = 'CLI-Top'
        tv2 = 'kitchens-plus'
        tv3 = 'master'

        # See the file my_test_kitchen_list_by_exec_command.py.template, strip off the templat
        # then choose one of the calling patterns seen in the file.
        rv = check_output(my_exec_cmd)
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_a_kitchen_list(self):
        tv1 = 'CLI-Top'
        tv2 = 'kitchens-plus'
        tv3 = 'master'
        runner = CliRunner()
        result = runner.invoke(dk, ['kitchen-list'])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_kitchen_which(self):

        kn = 'bobo'
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        DKKitchenDisk.write_kitchen(kn, temp_dir)
        os.chdir(os.path.join(temp_dir, kn))

        runner = CliRunner()
        result = runner.invoke(dk, ['kitchen-which'])
        self.assertTrue(0 == result.exit_code)
        self.assertIn('bobo', result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kitchen_get(self):
        tk = 'CLI-Top'
        recipe1 = 'simple'
        recipe2 = 'parallel-recipe-test'
        runner = CliRunner()

        # temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        # os.chdir(temp_dir)
        # result = runner.invoke(dk, ['kitchen-get', tk, '--all'])
        # self.assertTrue(0 == result.exit_code)
        # self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, recipe1)), True)
        # self.assertTrue('simple/node2/data_sinks' in result.output)
        # self.assertTrue('parallel-recipe-test/node1/data_sources' in result.output)
        # shutil.rmtree(temp_dir, ignore_errors=True)

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk, '--recipe', recipe1, '--recipe', recipe2])
        self.assertTrue(0 == result.exit_code)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, recipe1)), True)
        self.assertTrue('simple/node2/data_sinks' in result.output)
        self.assertTrue('parallel-recipe-test/node1/data_sources' in result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk])
        self.assertTrue(0 == result.exit_code)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, '.dk')), True)
        self.assertEqual(os.path.isfile(os.path.join(temp_dir, tk, '.dk', 'KITCHEN_META')), True)
        shutil.rmtree(temp_dir, ignore_errors=True)

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk, '--recipe', recipe1])
        self.assertTrue(0 == result.exit_code)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, recipe1)), True)
        self.assertTrue('simple/node2/data_sinks' in result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kitchen_create(self):
        parent = 'CLI-Top'
        kitchen = 'temp-create-kitchen-CL'
        kitchen = self._add_my_guid(kitchen)
        runner = CliRunner()

        runner.invoke(dk, ['kitchen-delete', kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertTrue(0 == result.exit_code)
        result2 = runner.invoke(dk, ['kitchen-list'])
        self.assertTrue(0 == result2.exit_code)
        rv = result2.output
        self.assertTrue(kitchen in rv)  # kitchen should be in the list

        result = runner.invoke(dk, ['kitchen-delete', kitchen])
        self.assertTrue(0 == result.exit_code)

    def test_kitchen_delete(self):
        parent = 'CLI-Top'
        kitchen = 'temp-delete-kitchen-CL'
        kitchen = self._add_my_guid(kitchen)
        runner = CliRunner()

        runner.invoke(dk, ['kitchen-delete', kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertTrue(0 == result.exit_code)

        result = runner.invoke(dk, ['kitchen-delete', kitchen])
        self.assertTrue(0 == result.exit_code)
        result2 = runner.invoke(dk, ['kitchen-list'])
        self.assertTrue(0 == result2.exit_code)
        self.assertTrue(kitchen not in result2.output)  # kitchen should not be in the list

    def test_recipe_list(self):
        tv1 = 's3-small-recipe'
        tv2 = 'simple'
        tv3 = 'parallel-recipe-test'
        kitchen_name = 'CLI-Top'
        runner = CliRunner()
        result = runner.invoke(dk, ['recipe-list', '--kitchen', kitchen_name])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        result = runner.invoke(dk, ['recipe-list'])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get(self):
        tv = 'simple'
        kn = 'CLI-Top'

        temp_dir, kitchen_dir = self._make_kitchen_dir(kn, change_dir=True)

        runner = CliRunner()
        result = runner.invoke(dk, ['recipe-get', tv])
        rv = result.output
        self.assertTrue(tv in rv)
        self.assertTrue(os.path.exists(tv))
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_status(self):
        tv = 'simple'
        kn = 'CLI-Top'
        runner = CliRunner()

        # Get something to compare against.
        temp_dir, kitchen_dir = self._make_kitchen_dir(kn, change_dir=True)
        runner.invoke(dk, ['recipe-get', tv])

        new_path = os.path.join(kitchen_dir, tv)
        os.chdir(new_path)
        result = runner.invoke(dk, ['recipe-status'])
        self.assertEqual(result.exit_code, 0)
        self.assertFalse('error' in result.output)

        match = re.search(r"([0-9]*) files are unchanged", result.output)
        self.assertTrue(int(match.group(1)) >= 15)
        self.assertTrue('files are unchanged' in result.output)

        os.chdir(os.path.split(new_path)[0])
        result = runner.invoke(dk, ['recipe-status'])
        self.assertTrue('error' in result.output.lower())
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_all_files(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_update_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test update CLI-test_update_file'
        api_file_key = file_name
        update_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        runner = CliRunner()  # for the CLI level
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(parent_kitchen, temp_dir)
        parent_kitchen_dir = os.path.join(temp_dir, parent_kitchen)
        os.chdir(parent_kitchen_dir)
        original_file = self._get_recipe_file_contents(runner, parent_kitchen, recipe_name, recipe_file_key, file_name)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        test_kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(test_kitchen_dir)
        new_kitchen_file = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                          recipe_file_key, file_name, temp_dir)
        self.assertEqual(original_file, new_kitchen_file)
        new_kitchen_file_dict = self._get_the_dict(new_kitchen_file)
        new_kitchen_file_abspath = os.path.join(test_kitchen_dir, os.path.join(recipe_file_key, file_name))
        new_kitchen_file_dict[test_kitchen] = update_str
        new_kitchen_file2 = self._get_the_json_str(new_kitchen_file_dict)
        with open(new_kitchen_file_abspath, 'w') as rfile:
            rfile.seek(0)
            rfile.truncate()
            rfile.write(new_kitchen_file2)
        # test
        orig_dir = os.getcwd()
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        result = runner.invoke(dk, ['recipe-update', '--message', message])
        os.chdir(orig_dir)
        self.assertTrue('ERROR' not in result.output)
        new_kitchen_file3 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                           recipe_file_key, file_name)
        self.assertEqual(new_kitchen_file2, new_kitchen_file3)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_update_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test update CLI-test_update_file'
        api_file_key = file_name
        update_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        runner = CliRunner()  # for the CLI level
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(parent_kitchen, temp_dir)
        parent_kitchen_dir = os.path.join(temp_dir, parent_kitchen)
        os.chdir(parent_kitchen_dir)
        original_file = self._get_recipe_file_contents(runner, parent_kitchen, recipe_name, recipe_file_key, file_name)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        test_kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(test_kitchen_dir)
        new_kitchen_file = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                          recipe_file_key, file_name, temp_dir)
        self.assertEqual(original_file, new_kitchen_file)
        new_kitchen_file_dict = self._get_the_dict(new_kitchen_file)
        new_kitchen_file_abspath = os.path.join(test_kitchen_dir, os.path.join(recipe_file_key, file_name))
        new_kitchen_file_dict[test_kitchen] = update_str
        new_kitchen_file2 = self._get_the_json_str(new_kitchen_file_dict)
        with open(new_kitchen_file_abspath, 'w') as rfile:
            rfile.seek(0)
            rfile.truncate()
            rfile.write(new_kitchen_file2)
        # test
        orig_dir = os.getcwd()
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        result = runner.invoke(dk, ['file-update',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    api_file_key])
        os.chdir(orig_dir)
        self.assertTrue('ERROR' not in result.output)
        new_kitchen_file3 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                           recipe_file_key, file_name)
        self.assertEqual(new_kitchen_file2, new_kitchen_file3)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_file(self):
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'test_create_file-Runner'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        file_name = 'added.sql'
        filedir = 'resources'
        recipe_file_key = os.path.join(recipe_name, filedir)
        api_file_key = os.path.join(filedir, file_name)
        file_contents = '--\n-- sql for you\n--\n\nselect 1024\n\n'
        message = 'test update test_create_file-API'
        runner = CliRunner()

        # create test kitchen
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir = tempfile.mkdtemp(prefix='unit-test_create_file', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kd = os.path.join(temp_dir, test_kitchen)
        orig_dir = os.getcwd()
        os.chdir(kd)
        self._get_recipe(runner, recipe_name)

        # create new file on disk
        try:
            os.chdir(recipe_name)
            f = open(api_file_key, 'w')
            f.write(file_contents)
            f.close()
        except ValueError, e:
            print('could not write file %s.' % e)
            self.assertTrue(False)

        # add file from disk THE TEST
        result = runner.invoke(dk, ['file-add',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    api_file_key
                                    ])
        self.assertTrue('ERROR' not in result.output)

        # make sure file is in kitchen (get file)
        file_contents2 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(file_contents, file_contents2, 'Create check')

        # cleanup
        os.chdir(orig_dir)
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_top(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_top'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = ' test Delete CLI-test_delete_file_top'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)
        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    file_name
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       recipe_file_key, file_name, temp_dir) is None, "Found the file")
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_deeper(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_deeper'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = 'resources/very_cool.sql'
        file_name = 'very_cool.sql'
        message = ' test Delete CLI-test_delete_file_deeper'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)

        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    recipe_file_key
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       os.path.join(recipe_name, recipe_file_key), file_name,
                                                       temp_dir) is None)
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_deeper_multi(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_deeper_multi'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = 'resources/very_cool.sql'
        file_name = 'very_cool.sql'
        file2 = 'description.json'
        message = ' test Delete CLI-test_delete_file_deeper_multi'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertTrue(0 == result.exit_code)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)

        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    recipe_file_key,
                                    file2
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       os.path.join(recipe_name, recipe_file_key), file_name,
                                                       temp_dir) is None)
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_compiled_serving_from_recipe(self):
        # setup
        parent_kitchen = 'master'
        new_kitchen = 'test_get_compiled_serving_from_recipe-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = 'variation-test'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)
        # test
        resp = runner.invoke(dk, ['recipe-compile',
                                  '--kitchen', new_kitchen,
                                  '--recipe', recipe_name,
                                  '--variation', variation_name])
        self.assertTrue(0 == result.exit_code)
        # cleanup
        result = runner.invoke(dk, ['kitchen-delete', new_kitchen])
        self.assertTrue(0 == result.exit_code)

    def test_merge_kitchens_success(self):
        existing_kitchen_name = 'master'
        base_test_kitchen_name = 'base-test-kitchen'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = 'branched-from-base-test-kitchen'
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)

        # setup
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', branched_test_kitchen_name])
        runner.invoke(dk, ['kitchen-delete', base_test_kitchen_name])
        # test
        # create base kitchen
        result = runner.invoke(dk, ['kitchen-create', '-p', existing_kitchen_name,
                                    base_test_kitchen_name])
        self.assertTrue(0 == result.exit_code)
        # create branch kitchen from base kitchen
        result = runner.invoke(dk, ['kitchen-create', '-p', base_test_kitchen_name,
                                    branched_test_kitchen_name])
        self.assertTrue(0 == result.exit_code)
        # do merge
        result = runner.invoke(dk, ['kitchen-merge', '--source_kitchen', branched_test_kitchen_name,
                                    '--target_kitchen', base_test_kitchen_name])
        self.assertTrue(0 == result.exit_code)
        self._check_no_merge_conflicts(result.output)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', branched_test_kitchen_name])
        runner.invoke(dk, ['kitchen-delete', base_test_kitchen_name])

    # --------------------------------------------------------------------------------------------------------------------
    #  Order commands
    # --------------------------------------------------------------------------------------------------------------------

    def test_create_order(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = self._get_run_variation_for_recipe(recipe)
        runner = CliRunner()

        # create test kitchen
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', kitchen,
                                    '--recipe', recipe,
                                    variation])
        self.assertTrue(0 == result.exit_code)
        self.assertTrue('simple' in result.output)

    def test_create_order_one_node(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        node = 'node2'
        variation = self._get_run_variation_for_recipe(recipe)
        runner = CliRunner()

        # create test kitchen
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', kitchen,
                                    '--recipe', recipe,
                                    '--node', node,
                                    variation])
        self.assertTrue(0 == result.exit_code)
        self.assertTrue('simple' in result.output)

    # Delete Order Testing ------

    def test_delete_all_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderCLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])  # clean up junk
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, variation])
        self.assertTrue(0 == result.exit_code)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[1].strip()
        self.assertIsNotNone(variation in order_id)
        # test
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen', new_kitchen])
        self.assertTrue(0 == result.exit_code)
        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen])

    def test_delete_one_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderCLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])  # clean up junk
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, variation])
        self.assertTrue(0 == result.exit_code)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[5].strip()
        self.assertIsNotNone(variation in order_id)
        # test
        result = runner.invoke(dk, ['order-delete',
                                    '--order_id', order_id])
        self.assertTrue(0 == result.exit_code)
        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen])

    def test_order_stop(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'stop-da-order-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'test-everything-recipe'
        # variation = 'variation-test-production05'
        variation = 'variation-morning-prod05'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])  # clean up junk
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, variation])
        self.assertTrue(0 == result.exit_code)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[5].strip()
        self.assertIsNotNone(variation in order_id)
        # test
        time.sleep(2)
        # result_before = runner.invoke(dk, ['orderrun-info',
        #                             '--kitchen', new_kitchen,
        #                             '--runstatus'])
        result_stop = runner.invoke(dk, ['order-stop',
                                         '--order_id', order_id])
        # result_after = runner.invoke(dk, ['orderrun-info',
        #                             '--kitchen', new_kitchen,
        #                             '--runstatus'])

        ## FIXED?? for now accept that this does not work
        self.assertTrue(0 == int(result_stop.exit_code))
        # self.assertIsNotNone('OrderStopV2: unable to stop order' in result_stop.output)
        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen])

    def test_delete_order_bad_order_id(self):
        order_id = 'junk'
        runner = CliRunner()
        result = runner.invoke(dk, ['order-delete',
                                    '--order_id', order_id])
        self.assertTrue(0 != result.exit_code)
        self.assertTrue('Error: unable to delete order id junk' in result.output)

    def test_delete_order_bad_kitchen(self):
        kitchen = 'junk'
        runner = CliRunner()
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen', kitchen])
        self.assertTrue(0 != result.exit_code)
        self.assertTrue('Error: unable to delete orders in kitchen junk' in result.output)

    # test illegal command line combo
    def test_orderrun_detail_bad_command(self):
        kitchen = 'ppp'
        runner = CliRunner()
        result = runner.invoke(dk, ['orderrun-info',
                                    '--kitchen', kitchen,
                                    '-o', 'o', '-r', 'r'])
        self.assertTrue(0 != result.exit_code)
        self.assertTrue('Error' in result.output)



    def test_list_order(self):
        kitchen = 'CLI-Top'
        runner = CliRunner()

        # create test kitchen
        result = runner.invoke(dk, ['order-list',
                                    '--kitchen', kitchen])
        # This is a bit of a token test to make sure we get something back. Don't care what.
        self.assertTrue(0 == result.exit_code)

    def test_orderrun_stop(self):
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_orderrun_stop-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)

        # start order & order run
        print 'Starting Create-Order in test_orderrun_stop()'
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', new_kitchen,
                                    '--recipe', recipe_name,
                                    variation_name])
        self.assertTrue(0 == result.exit_code)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[1].strip()
        self.assertIsNotNone(variation_name in order_id)
        wait_time = [.1, 1, 1, 2, 2, 2, 4, 4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        # wait for state "ACTIVE_SERVING"
        # not going to try for "PLANNED_SERVING" because that may go by too fast
        found_active_serving = False
        wait_generator = (wt for wt in wait_time if found_active_serving is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp1.output is not None:
                print '(%i) got %s' % (wt, resp1.output)
                if "ACTIVE_SERVING" in resp1.output:
                    found_active_serving = True
        self.assertTrue(found_active_serving)
        print 'test_orderrun_stop: found_active_serving is True'

        resp2 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--disp_order_run_id'])
        orderrun_id = resp2.output
        resp3 = runner.invoke(dk, ['orderrun-stop', '-r', orderrun_id])
        self.assertTrue(0 == resp3.exit_code)

        # check to make sure the serving is in the "STOPPED_SERVING" state

        found_stopped_state = False
        wait_generator = (wt for wt in wait_time if found_stopped_state is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp4 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp4.output is not None:
                print '(%i) got %s' % (wt, resp4.output)
                if "STOPPED_SERVING" in resp4.output:
                    found_stopped_state = True
        print 'test_orderrun_stop: found_stopped_state is True'
        self.assertTrue(found_stopped_state)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen])

    def test_wait_for_serving_states(self):
        # setup
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_scenario_orderrun_stop-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertTrue(0 == result.exit_code)

        # start order & order run
        print 'Starting Create-Order in test_scenario_orderrun_stop()'
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', new_kitchen,
                                    '--recipe', recipe_name,
                                    variation_name])
        self.assertTrue(0 == result.exit_code)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[1].strip()
        self.assertIsNotNone(variation_name in order_id)
        wait_time = [.1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        # wait for state "ACTIVE_SERVING"
        # not going to try for "PLANNED_SERVING" because that may go by too fast
        found_active_serving = False
        wait_generator = (wt for wt in wait_time if found_active_serving is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp1.output is not None:
                print '(%i) got %s' % (wt, resp1.output)
                if "ACTIVE_SERVING" in resp1.output:
                    found_active_serving = True
        self.assertTrue(found_active_serving)
        print 'test_scenario_orderrun_stop: found_active_serving is True'

        # wait for state "COMPLETED_SERVING"
        found_completed_serving = False
        wait_generator = (wt for wt in wait_time if found_completed_serving is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp2 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp2.output is not None:
                print '(%i) got %s' % (wt, resp2.output)
                if "COMPLETED_SERVING" in resp2.output:
                    found_completed_serving = True
        self.assertTrue(found_completed_serving)
        print 'test_scenario_orderrun_stop: found_completed_serving is True'

        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen])

        # helpers ---------------------------------

    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(str(resp).find('diverged') < 0)

    def _get_recipe_file_contents(self, runner, kitchen, recipe_name, recipe_file_key, file_name, temp_dir=None):
        delete_temp_dir = False
        if temp_dir is None:
            td = tempfile.mkdtemp(prefix='unit-tests-grfc', dir=TestCommandLine._TEMPFILE_LOCATION)
            delete_temp_dir = True
            DKKitchenDisk.write_kitchen(kitchen, td)
            kitchen_directory = os.path.join(td, kitchen)
        else:
            td = temp_dir
            kitchen_directory = os.getcwd()
        cwd = os.getcwd()
        os.chdir(kitchen_directory)
        result = runner.invoke(dk, ['recipe-get', recipe_name])
        os.chdir(cwd)
        rv = result.output
        self.assertTrue(recipe_name in rv)
        abspath = os.path.join(td, os.path.join(kitchen, recipe_file_key, file_name))
        if os.path.isfile(abspath):
            with open(abspath, 'r') as rfile:
                rfile.seek(0)
                the_file = rfile.read()
            rc = the_file
        else:
            rc = None
        if delete_temp_dir is True:
            shutil.rmtree(td, ignore_errors=True)
        return rc

    def _get_recipe(self, runner, recipe):
        result = runner.invoke(dk, ['recipe-get', recipe])
        rv = result.output
        self.assertTrue(recipe in rv)
        return True


if __name__ == '__main__':
    unittest.main()
