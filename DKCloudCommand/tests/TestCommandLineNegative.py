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

if '../cli/' not in path:
    path.insert(0, '../cli/')
from dk import dk


class TestCommandLineNegative(BaseTestCloud):
    _TEMPFILE_LOCATION = '/var/tmp'

    def test_imaginary_kitchen_delete(self):
        kitchen = 'garbage-name'
        runner = CliRunner()
        result = runner.invoke(dk, ['kitchen-delete', kitchen])
        self.assertTrue(0 != result.exit_code)
        self.assertTrue('Error' in result.output)


    def test_kitchen_create_duplicates(self):
        parent = 'CLI-Top'
        kitchen = self._add_my_guid('double')
        runner = CliRunner()

        runner.invoke(dk, ['kitchen-delete', kitchen])
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertTrue(0 == result.exit_code)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertTrue(0 != result.exit_code) # should not work the second time
        result = runner.invoke(dk, ['kitchen-delete', kitchen])
        self.assertTrue(0 == result.exit_code)

    def test_active_serving_delete_bad_kitchen(self):
        kitchen = self._add_my_guid('notakitchen')
        runner = CliRunner()
        result = runner.invoke(dk, ['active-serving-delete', kitchen])
        self.assertTrue(0 != result.exit_code)

    def test_completed_serving_delete_bad_kitchen(self):
        kitchen = self._add_my_guid('notakitchen')
        runner = CliRunner()
        result = runner.invoke(dk, ['completed-serving-delete', kitchen])
        self.assertTrue(0 != result.exit_code)

    def test_completed_serving_copy_bad_inputs(self):
        source = self._add_my_guid('notSrc')
        target = self._add_my_guid('notTarget')
        id = self._add_my_guid('notId')
        runner = CliRunner()
        result = runner.invoke(dk, ['completed-serving-copy', '-s', source, '-t', target, '-id', id])
        self.assertTrue(0 != result.exit_code)

#    def test_get_kitchen2(self):
#        kitchen = 'giltest'
#        recipe = 'test-everything-recipe'
#        runner = CliRunner()
#        result = runner.invoke(dk, ['kitchen-get', '-r', recipe, kitchen])
#        self.assertTrue(0 == result.exit_code)

    # helpers ---------------------------------
    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(str(resp).find('diverged') < 0)

    def _get_recipe_file_contents(self, runner, kitchen, recipe_name, recipe_file_key, file_name, temp_dir=None):
        delete_temp_dir = False
        if temp_dir is None:
            td = tempfile.mkdtemp(prefix='unit-tests-grfc', dir=TestCommandLine._TEMPFILE_LOCATION)
            delete_temp_dir = True
        else:
            td = temp_dir
        cwd = os.getcwd()
        os.chdir(td)
        result = runner.invoke(dk, ['recipe-get', '--kitchen', kitchen, '--recipe', recipe_name])
        os.chdir(cwd)
        rv = result.output
        self.assertTrue(recipe_name in rv)
        abspath = os.path.join(td, os.path.join(recipe_file_key, file_name))
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

    def _get_recipe(self, runner, kitchen, recipe):
        result = runner.invoke(dk, ['recipe-get', '--kitchen', kitchen, '--recipe', recipe])
        rv = result.output
        self.assertTrue(recipe in rv)
        return True


if __name__ == '__main__':
    unittest.main()
