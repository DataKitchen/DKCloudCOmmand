import re
import unittest
import datetime, time
import tempfile
import pickle
from sys import path, stdout
import os
import shutil

# if '../../' not in path:
#    path.insert(0, '../../')
from BaseTestCloud import BaseTestCloud
from DKCloudCommandRunner import DKCloudCommandRunner
from DKActiveServingWatcher import *
from DKCloudAPIMock import DKCloudAPIMock


class TestCloudCommandRunner(BaseTestCloud):
    def test_rude(self):
        tv = 'DKCloudCommand.rude = **rude**\n'
        rv = DKCloudCommandRunner.rude(self._api)
        self.assertIsNotNone(rv)
        self.assertEqual(rv, tv)

        rv = DKCloudCommandRunner.rude(BaseTestCloud)
        self.assertIn('ERROR', rv)

    def test_a_list_kitchens(self):
        tv1 = 'CLI-Top'
        tv2 = 'kitchens-plus'
        tv3 = 'master'
        # tv = 'DKCloudCommand.kitchens returned 3 kitchens\n  base-test-kitchen \n  kitchens-plus \n  master \n'
        rc = DKCloudCommandRunner.list_kitchen(self._api)
        self.assertTrue(rc.ok())
        rv = rc.get_message()
        self.assertTrue(isinstance(rv, basestring))
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_get_kitchen(self):
        tk = 'CLI-Top'

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=self._TEMPFILE_LOCATION)

        kitchen_path = os.path.join(temp_dir, tk)
        os.makedirs(kitchen_path)

        # kitchen dir already has a folder in it.
        bad_path = os.path.join(kitchen_path, 'bad')
        os.makedirs(bad_path)
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertFalse(rv.ok())
        shutil.rmtree(bad_path, ignore_errors=True)

        # kitchen dir already has a file in it.
        with open(os.path.join(kitchen_path, 'bad.txt'), 'w') as bad_file:
            bad_file.write('bad.txt')
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertFalse(rv.ok())
        shutil.rmtree(kitchen_path, ignore_errors=True)

        # kitchen dir exists, but is empty
        kitchen_path = os.path.join(temp_dir, tk)
        os.makedirs(kitchen_path)
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertTrue(rv.ok())
        self.assertEqual(os.path.isdir(os.path.join(kitchen_path, '.dk')), True)
        shutil.rmtree(kitchen_path, ignore_errors=True)

        # kitchen dir does not exists.
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertTrue(rv.ok())
        self.assertEqual(os.path.isdir(os.path.join(kitchen_path, '.dk')), True)

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_which_kitchen(self):
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=self._TEMPFILE_LOCATION)
        kn = 'fake'
        kp = os.path.join(temp_dir, kn)
        os.makedirs(kp)
        dk = os.path.join(kp, '.dk')
        os.makedirs(dk)
        with open(os.path.join(dk, 'KITCHEN_META'), 'w') as meta:
            meta.write(kn)

        rv = DKCloudCommandRunner.which_kitchen(self._api, path=kp)
        self.assertIn('You are in', rv.get_message())

        rv = DKCloudCommandRunner.which_kitchen(self._api, kp)
        self.assertIn('You are in', rv.get_message())

        rv = DKCloudCommandRunner.which_kitchen(temp_dir)
        self.assertFalse(rv.ok())


    def test_create_kitchen(self):
        parent = 'CLI-Top'
        kitchen = 'temp-create-kitchen-Runner'
        kitchen = self._add_my_guid(kitchen)

        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)
        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())
        rc = DKCloudCommandRunner.list_kitchen(self._api)
        rv2 = rc.get_message()
        self.assertTrue(kitchen in rv2)
        # cleanup
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)

    def test_delete_kitchen(self):
        parent = 'CLI-Top'
        kitchen = 'temp-delete-kitchen-Runner'
        kitchen = self._add_my_guid(kitchen)
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)

        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())

        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertTrue(rv.ok())
        rc = DKCloudCommandRunner.list_kitchen(self._api)
        rv2 = rc.get_message()
        self.assertTrue(kitchen not in rv2)

    def test_recipe_list(self):
        tv1 = 's3-small-recipe'
        tv2 = 'simple'
        tv3 = 'parallel-recipe-test'
        rc = DKCloudCommandRunner.list_recipe(self._api, 'CLI-Top')
        rv = rc.get_message()
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_recipe_get(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        rv = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        self.assertTrue(recipe_name in rv.get_message())
        self.assertTrue('sections' in rv.get_message())
        self.assertTrue(os.path.exists(os.path.join(kitchen_dir, recipe_name)))
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_dir_exists(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, kitchen_dir, recipe_dir = self._make_recipe_dir(recipe_name, kitchen_name, change_dir=True)
        rv = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        msg = rv.get_message()
        self.assertTrue(recipe_name in msg)
        matches = re.match(r"([0-9]*) new or missing files", msg)
        self.assertTrue(int(matches.group(1)) >= 16)
        self.assertTrue('new or missing files' in msg)
        self.assertTrue(os.path.exists(os.path.join(kitchen_dir, recipe_name)))
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_negative(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple_fogfogkfok'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        self.assertFalse(rc.ok())
        self.assertTrue('not in kitchen' in rc.get_message().lower())
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_complex(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        recipe_path = os.path.join(kitchen_dir, recipe_name)
        self.assertTrue(os.path.exists(recipe_path))

        # Modify the local file.
        with open(os.path.join(recipe_path, "simple-file.txt"), 'a') as modify_file:
            modify_file.write('new line\n')
            modify_file.flush()

        # Delete something local, so it's remote only.
        os.remove(os.path.join(recipe_path, 'variations.json'))
        os.remove(os.path.join(recipe_path, 'node1', 'data_sources', 'DKDataSource_NoOp.json'))

        # Create a new file, so there is a local only file.
        with open(os.path.join(recipe_path, "new_local_file.txt"), 'w') as new_local_file:
            new_local_file.write('peccary\n')
            new_local_file.flush()

        subdir = os.path.join(recipe_path, 'subdir')
        os.mkdir(subdir)
        with open(os.path.join(subdir, "new_local_file_in_subdir.txt"), 'w') as new_local_file:
            new_local_file.write('peccary\n')
            new_local_file.flush()

        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, recipe_path)
        self.assertTrue(rc.ok())
        msg = rc.get_message()
        self.assertTrue('Auto-merging' in msg)
        self.assertTrue('2 new or missing files' in msg)
        if False:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_status(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'

        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)

        new_path = os.path.join(kitchen_dir, recipe_name)
        os.chdir(new_path)

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name)
        rs = rc.get_message()
        self.assertNotRegexpMatches(rs, '^ERROR')
        matches = re.match(r"([0-9]*) files are unchanged", rs)
        self.assertTrue(int(matches.group(1)) >= 16)
        self.assertTrue('files are unchanged' in rs)

        # Modify existing file
        with open(os.path.join(new_path, 'node1/description.json'), 'w') as f:
            f.write('BooGa BooGa')
        # Add a new file
        with open(os.path.join(new_path, 'node1/newfile.json'), 'w') as f:
            f.write('This is my new file. Hooray!')
        # Delete a file
        os.remove(os.path.join(new_path, 'node1/post_condition.json'))
        # Remove a directory
        shutil.rmtree(os.path.join(new_path, 'node1/data_sinks'))

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name)
        rs = rc.get_message()
        self.assertNotRegexpMatches(rs, '^ERROR')
        match = re.search(r"([0-9]*) files are unchanged", rs)
        self.assertTrue(int(match.group(1)) >= 15)
        self.assertTrue('files are unchanged' in rs)

        self.assertTrue('1 files are modified' in rs)
        self.assertTrue('1 files are local only' in rs)
        self.assertTrue('1 files are remote only' in rs)
        self.assertTrue('1 directories are remote only' in rs)

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

        # Cleanup old state
        self._delete_and_clean_kitchen(test_kitchen)

        # Get the original file. Helper function handles the directories.
        original_file = self._get_recipe_file(parent_kitchen, recipe_name, recipe_file_key, file_name)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # Get the new kitchen to a temp folder
        temp_dir, test_kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)
        new_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name,
                                                 test_kitchen_dir)
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
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        rc = DKCloudCommandRunner.update_file(self._api, test_kitchen, recipe_name, message, api_file_key)
        self.assertTrue(rc.ok())
        new_kitchen_file3 = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(new_kitchen_file2, new_kitchen_file3)

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_util_funcs(self):

        paths_to_check = ['description.json', 'graph.json', 'simple-file.txt', 'node2_hide', 'node2_hide/my_file.txt', 'node1hide/subdir/hide-me.txt''variables.json', 'variations.json', 'node2/data_sinks', 'node1/data_sinks', 'node2', 'node1', 'node1/data_sources', 'resources', 'node2/data_sources']
        minimal_paths = DKCloudCommandRunner.find_minimal_paths_to_get(paths_to_check)
        self.assertIsNotNone(minimal_paths)

    def test_update_all(self):
        parent_kitchen = 'CLI-Top'
        test_kitchen = self._add_my_guid('update_all')
        recipe_name = 'simple'
        new = 'new.txt'
        deleted = 'deleted.txt'
        modified = 'modified.txt'
        subdir = 'subdir'
        subsubdir = os.path.join(subdir, 'subsubdir')
        subusubsubdir = os.path.join(subsubdir, 'subusubsubdir')

        self._delete_and_clean_kitchen(test_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir, kitchen_dir, recipe_dir = self._make_recipe_dir(recipe_name, test_kitchen)
        os.chdir(kitchen_dir)
        print 'Working in directory %s' % recipe_dir
        start_time = time.time()
        rs = DKCloudCommandRunner.get_recipe(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'get_recipe - elapsed: %d' % elapsed_recipe_status
        self.assertTrue(rs.ok())

        os.chdir(recipe_dir)
        start_time = time.time()
        rc = DKCloudCommandRunner.recipe_status(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'recipe_status - elapsed: %d' % elapsed_recipe_status
        msg = rc.get_message()
        self.assertTrue('files differ' not in msg)
        self.assertTrue('only on local' not in msg)
        self.assertTrue('only on remote' not in msg)

        # New, not added, file
        with open(new, 'w') as f:
            f.write('This is file %s\n' % new)

        with open(os.path.join('node1', new), 'w') as f:
            f.write('This is file %s in node 1\n' % new)

        # Deleted File
        with open(deleted, 'w') as f:
            f.write('This is file %s\n' % deleted)
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, 'Adding %s' % deleted, deleted)
        self.assertTrue(rc.ok())
        os.remove(deleted)

        # Modified File
        with open(modified, 'w') as f:
            f.write('This is file %s\n' % modified)
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, 'Adding %s' % modified, modified)
        self.assertTrue(rc.ok())

        with open(modified, 'a') as f:
            f.write('This is a new line %s\n' % modified)

        # New file in a subdirectory
        os.mkdir(subdir)
        os.mkdir(subsubdir)
        os.mkdir(subusubsubdir)

        with open(os.path.join(subsubdir, new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % (new, subsubdir))

        with open(os.path.join(subsubdir, 'also_%s' % new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % ('also_%s' % new, subsubdir))

        with open(os.path.join(subusubsubdir, 'again_%s' % new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % ('also_%s' % new, subusubsubdir))

        # Delete a whole directory, and some files under there.
        shutil.rmtree('node1', ignore_errors=True)

        # Make sure repo is in state we expect.
        start_time = time.time()
        rc = DKCloudCommandRunner.recipe_status(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'recipe_status - elapsed: %d' % elapsed_recipe_status
        msg = rc.get_message()

        match = re.search(r"([0-9]*) files are unchanged", msg)
        self.assertTrue(int(match.group(1)) >= 10)
        self.assertTrue('files are unchanged' in msg)

        match = re.search(r"([0-9]*) files are modified", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are modified' in msg)

        match = re.search(r"([0-9]*) files are local only", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are local only' in msg)

        match = re.search(r"([0-9]*) files are remote only", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are remote only' in msg)

        self.assertTrue('subdir/subsubdir/subusubsubdir' in msg)

        start_time = time.time()
        rc = DKCloudCommandRunner.update_all_files(self._api, test_kitchen, recipe_name, recipe_dir, 'update all dryrun', dryrun=True)
        elapsed_recipe_status = time.time() - start_time
        print 'update_all_files - elapsed: %d' % elapsed_recipe_status

        self.assertTrue(rc.ok())
        msg = rc.get_message()
        self.assertTrue('modified.txt' in msg)
        self.assertTrue('new.txt' in msg)
        self.assertTrue('deleted.txt' in msg)
        self.assertTrue('subdir/subsubdir/new.txt' in msg)
        self.assertTrue('subdir/subsubdir/subusubsubdir/again_new.txt' in msg)

        start_time = time.time()
        rc = DKCloudCommandRunner.update_all_files(self._api, test_kitchen, recipe_name, recipe_dir, 'update all')
        elapsed_recipe_status = time.time() - start_time
        print 'update_all_files - elapsed: %d' % elapsed_recipe_status

        self.assertTrue(rc.ok())
        msg = rc.get_message()
        self.assertTrue('modified.txt' in msg)
        match = re.search(r"([0-9]*) files updated", msg)
        self.assertTrue(int(match.group(1)) >= 1)

        self.assertTrue('subdir/subsubdir/new.txt' in msg)
        match = re.search(r"([0-9]*) files added", msg)
        self.assertTrue(int(match.group(1)) >= 4)

        self.assertTrue('node1/data_sources/DKDataSource_NoOp.json' in msg)
        match = re.search(r"([0-9]*) files deleted", msg)
        self.assertTrue(int(match.group(1)) >= 7)

        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_file(self):
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

        # test negative
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, message, 'badfile.txt')
        self.assertFalse(rc.ok())

        # create test kitchen
        self._delete_and_clean_kitchen(test_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir, kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)
        os.chdir(kitchen_dir)
        self._get_recipe(test_kitchen, recipe_name)

        # create new file on disk
        try:
            os.chdir(recipe_name)
            with open(api_file_key, 'w') as f:
                f.write(file_contents)
        except ValueError, e:
            print('could not write file %s.' % e)
            self.assertTrue(False)

        # add file from disk THE TEST
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, message, api_file_key)
        self.assertTrue(rc.ok())

        # make sure file is in kitchen (get file)
        file_contents2 = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(file_contents, file_contents2, 'Create check')

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'Runner-test_delete_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test Delete Runner-test_delete_file'
        self._delete_and_clean_kitchen(test_kitchen)
        temp_dir, kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())
        os.chdir(kitchen_dir)

        self.assertTrue(self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name) is not None)
        rv = DKCloudCommandRunner.get_recipe(self._api, test_kitchen, recipe_name)
        self.assertTrue(recipe_name in rv.get_message())
        target_file = os.path.join(kitchen_dir, os.path.join(recipe_file_key, file_name))
        self.assertTrue(os.path.isfile(target_file))  # the file is there
        os.remove(target_file)
        rs = DKCloudCommandRunner.delete_file(self._api, test_kitchen, recipe_name,
                                              message, file_name)
        self.assertTrue(rs.ok())
        self.assertTrue(self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name) is None,
                        "Gone check")

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    # def test_cook_recipe_recipe(self):
    #     kitchen = 'CLI-Top'
    #     recipe = 'simple'
    #     variation = 'simple-variation-now'
    #     rv = DKCloudCommandRunner.cook_recipe(self._api, kitchen, recipe, variation)
    #     self.assertTrue('started' in rv.get_message())

    def test_create_order(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = 'simple-variation-now'
        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe, variation)
        self.assertTrue('simple' in rv.get_message())

    def test_delete_all_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderRUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()
        self.assertIsNotNone(variation in order_id)
        # test
        rc = DKCloudCommandRunner.delete_all_order(self._api, new_kitchen)
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_delete_one_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_order-RUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()
        self.assertIsNotNone(variation in order_id)
        # test
        rc = DKCloudCommandRunner.delete_one_order(self._api, order_id)
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_stop_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_stop_order-RUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()
        self.assertIsNotNone(variation in order_id)
        # test
        rc = DKCloudCommandRunner.stop_order(self._api, order_id)
        # todo: need to find a way for this to succeed
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_get_compiled_serving_from_recipe(self):
        # setup
        parent_kitchen = 'master'
        new_kitchen = 'test_get_compiled_serving_from_recipe=API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = 'variation-test'
        self._delete_and_clean_kitchen(new_kitchen)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())
        # test
        resp = DKCloudCommandRunner.get_compiled_serving(self._api, parent_kitchen, recipe_name, variation_name)
        self.assertTrue(resp.ok())
        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    def test_merge_kitchens_success(self):
        existing_kitchen_name = 'master'
        base_test_kitchen_name = 'base-test-kitchen'
        branched_test_kitchen_name = 'branched-from-base-test-kitchen'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)

        # setup
        self._delete_and_clean_kitchen(branched_test_kitchen_name)
        self._delete_and_clean_kitchen(base_test_kitchen_name)
        # test
        # create base kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, base_test_kitchen_name)
        self.assertTrue(rs.ok())
        # create branch kitchen from base kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, base_test_kitchen_name, branched_test_kitchen_name)
        self.assertTrue(rs.ok())
        # do merge
        rd = DKCloudCommandRunner.merge_kitchens_improved(self._api, branched_test_kitchen_name, base_test_kitchen_name)
        self._check_no_merge_conflicts(rd)

        # cleanup
        self._delete_and_clean_kitchen(branched_test_kitchen_name)
        self._delete_and_clean_kitchen(base_test_kitchen_name)

    def test_merge_kitchens_improved_success(self):
        to_kitchen = 'dummy'
        from_kitchen = 'merge_success'

        mock_api = DKCloudAPIMock(self._cr_config)

        rv = DKCloudCommandRunner.merge_kitchens_improved(mock_api, from_kitchen, to_kitchen)
        self.assertTrue('1 files changed' in rv.get_message())
        self.assertTrue('1 insertions(+)' in rv.get_message())
        self.assertTrue('0 deletions(-)' in rv.get_message())
        # Check that the merge returned the diffs as expected.

    def test_merge_resolution(self):
        self.assertTrue(True)
        base_kitchen = 'CLI-Top'
        parent_kitchen = 'merge_resolve_parent'
        parent_kitchen = self._add_my_guid(parent_kitchen)
        child_kitchen = 'merge_resolve_child'
        child_kitchen = self._add_my_guid(child_kitchen)
        recipe = 'simple'
        conflicted_file = 'conflicted-file.txt'

        temp_dir_child, kitchen_dir_child, recipe_dir_child = self._make_recipe_dir(recipe, child_kitchen)
        temp_dir_parent, kitchen_dir_parent, recipe_dir_parent = self._make_recipe_dir(recipe, parent_kitchen)

        setup = True
        cleanup = True
        if setup:
            rc = DKCloudCommandRunner.delete_kitchen(self._api, child_kitchen)
            rc = DKCloudCommandRunner.delete_kitchen(self._api, parent_kitchen)

            rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen=base_kitchen, new_kitchen=parent_kitchen)
            self.assertTrue(rc.ok())
            rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen=parent_kitchen, new_kitchen=child_kitchen)
            self.assertTrue(rc.ok())

            os.chdir(recipe_dir_parent)
            # parent_file = os.path.join(recipe, conflicted_file)
            with open(conflicted_file, 'w') as f:
                f.write('line1\nparent\nline2\n')
            rc = DKCloudCommandRunner.add_file(self._api, parent_kitchen, recipe, 'adding %s to %s' % (conflicted_file, parent_kitchen), conflicted_file)
            self.assertTrue(rc.ok())

            os.chdir(recipe_dir_child)
            # child_file = os.path.join(recipe, conflicted_file)
            with open(conflicted_file, 'w') as f:
                f.write('line1\nchild\nline2\n')
            rc = DKCloudCommandRunner.add_file(self._api, child_kitchen, recipe, 'adding %s to %s' % (conflicted_file, child_kitchen), conflicted_file)
            self.assertTrue(rc.ok())

        # Make sure we are in the recipe folder before merging
        os.chdir(recipe_dir_child)
        rc = DKCloudCommandRunner.merge_kitchens_improved(self._api, child_kitchen, parent_kitchen)
        self.assertTrue('1 conflict found' in rc.get_message())
        self.assertTrue('simple/conflicted-file.txt' in rc.get_message())

        rc = DKCloudCommandRunner.merge_kitchens_improved(self._api, child_kitchen, parent_kitchen)
        self.assertTrue('Unresolved conflicts' in rc.get_message())
        self.assertTrue('conflicted-file.txt' in rc.get_message())

        rc = DKCloudCommandRunner.get_unresolved_conflicts(recipe, recipe_dir_child)
        self.assertTrue(rc.ok())
        self.assertTrue('Unresolved conflicts' in rc.get_message())

        rc = DKCloudCommandRunner.resolve_conflict(conflicted_file)
        self.assertTrue(rc.ok())
        self.assertTrue('Conflict resolved' in rc.get_message())

        rc = DKCloudCommandRunner.get_unresolved_conflicts(recipe, recipe_dir_child)
        self.assertTrue(rc.ok())
        self.assertTrue('No conflicts found' in rc.get_message())

        rc = DKCloudCommandRunner.merge_kitchens_improved(self._api, child_kitchen, parent_kitchen)
        self.assertTrue('Unresolved conflicts' not in rc.get_message())

        if cleanup:
            DKCloudCommandRunner.delete_kitchen(self._api, child_kitchen)
            DKCloudCommandRunner.delete_kitchen(self._api, parent_kitchen)
            shutil.rmtree(temp_dir_child, ignore_errors=True)
            shutil.rmtree(temp_dir_parent, ignore_errors=True)

    def test_merge_kitchens_improved_conflicts(self):
        to_kitchen_pickle = 'dummy'
        from_kitchen_pickle = 'merge_conflicts'
        mock_api = DKCloudAPIMock(self._cr_config)

        # This one tests just a print
        rv = DKCloudCommandRunner.merge_kitchens_improved(mock_api, from_kitchen_pickle, to_kitchen_pickle)
        self.assertTrue('1 conflict found' in rv.get_message())
        self.assertTrue('conflicted-file.txt' in rv.get_message())

        # Do the merge and put it down into a folder
        parent_kitchen = 'merge-parent_ut_6d887fc6'
        child_kitchen = 'merge-child_ut_6d887fc6'
        recipe_name = 'simple'
        temp_dir, kitchen_dir, recipe_dir = self._make_recipe_dir(recipe_name, child_kitchen)
        rv = DKCloudCommandRunner.merge_kitchens_improved(mock_api, child_kitchen, parent_kitchen)
        msg = rv.get_message()
        self.assertTrue('1 conflict found' in msg)
        self.assertTrue('conflicted-file.txt' in msg)
        with open(os.path.join(recipe_dir, 'conflicted-file.txt'), 'r') as conflicted_file:
            contents = conflicted_file.read()
            self.assertTrue('<<<<<<< your conflicted-file.txt' in contents)
            self.assertTrue('>>>>>>> their conflicted-file.txt' in contents)
            self.assertTrue('=======' in contents)

        # Now make sure it tells use there are unresolved conflicts the next time we try and merge
        rv = DKCloudCommandRunner.merge_kitchens_improved(mock_api, child_kitchen, parent_kitchen)
        self.assertTrue('Unresolved conflicts' in rv.rc['message'])
        self.assertTrue('conflicted-file.txt' in rv.rc['message'])

        # Resolve the conflict
        rc = DKCloudCommandRunner.resolve_conflict('conflicted-file.txt')
        self.assertTrue(rc.ok())

        # Now the conflict should be gone, and we should be back to the found conflicts and written to disk message.
        rc = DKCloudCommandRunner.merge_kitchens_improved(mock_api, child_kitchen, parent_kitchen)
        msg = rc.get_message()
        self.assertTrue('Unresolved conflicts' not in msg)
        self.assertTrue('1 conflict found' in msg)
        self.assertTrue('conflicted-file.txt' in msg)

        if temp_dir is not None and temp_dir != '/':
            shutil.rmtree(temp_dir)

    # # test helpers in DKCloudCommandRunner.py
    # def test__print_merge_patches_1(self):
    #     merge_conflicts = pickle.loads(open("files/merge_conflicts_1_file.p", "rb").read().replace('\r', ''))
    #     rs = DKCloudCommandRunner._print_merge_patches(merge_conflicts)
    #     # look for some strings so you know it worked
    #     # but don't look for too much so the test breaks if we re-format
    #     print rs
    #     self.assertTrue('File' in rs)
    #     self.assertTrue('parallel-recipe-test/description.json' in rs)
    #
    # def test__print_merge_patches_multi(self):
    #     merge_conflicts = pickle.loads(open("files/merge_conflicts_multi_file.p", "rb").read().replace('\r', ''))
    #     rs = DKCloudCommandRunner._print_merge_patches(merge_conflicts)
    #     # look for some strings so you know it worked
    #     # but don't look for too much so the test breaks if we re-format
    #     print rs
    #     self.assertTrue('File' in rs)
    #     self.assertTrue('simple/resources/very_cool.sql' in rs)
    #     self.assertTrue('parallel-recipe-test/description.json' in rs)
    #     self.assertTrue('parallel-recipe-test/node1/data_sources/DKDataSource_NoOp.json' in rs)

    def test_print_test_results(self):
        # good for more than acive
        rdict = pickle.loads(open("files/completed_serving_rdict.p", "rb").read().replace('\r', ''))
        # rdict = pickle.load(open("files/completed_serving_rdict_eg.p", "rb"))
        rs = DKCloudCommandRunner._print_test_results(rdict)
        # look for some strings so you know it worked
        # but don't look for too much so the test breaks if we re-format
        print rs
        self.assertTrue('File' in rs)

    def test_active_serving_watcher(self):
        # setup
        parent = 'master'
        kitchen = 'test_active_serving_watcher'
        kitchen = self._add_my_guid(kitchen)
        recipe_name = 'test-everything-recipe'
        variation_name = self._get_run_variation()
        self._delete_and_clean_kitchen(kitchen)

        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())

        # start watcher
        DKActiveServingWatcherSingleton().set_sleep_time(2)
        DKActiveServingWatcherSingleton().set_api(self._api)
        DKActiveServingWatcherSingleton().set_kitchen(kitchen)
        self.assertTrue(DKActiveServingWatcherSingleton().start_watcher())

        # cook one
        rs = DKCloudCommandRunner.create_order(self._api, kitchen, recipe_name, variation_name)
        self.assertTrue(rs.ok())
        wait_time = [.1, 1, 3, 3, 3, 3, 9, 18]
        found_active_serving = False
        wait_generator = (wt for wt in wait_time if found_active_serving is False)
        print 'test_active_serving_watcher: found_active_serving, trying ... '
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = DKCloudCommandRunner.orderrun_detail(self._api, kitchen, {'summary': True})
            print 'test_active_serving_watcher: found_active_serving is False (%s)' % wt
            # print 'got', resp1.get_message()
            message = resp1.get_message()
            if resp1.ok() and ('OrderRun is Planned' in message or 'OrderRun Completed' in message
                               or 'OrderRun is Active' in message):
                found_active_serving = True
        self.assertTrue(found_active_serving)

        # cleanup
        self._delete_and_clean_kitchen(kitchen)

    def test_user_info(self):
        rc = DKCloudCommandRunner.user_info(self._api)
        self.assertTrue(rc.ok())

    def test_order_list(self):
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_order_list'
        new_kitchen = self._add_my_guid(new_kitchen)
        self._delete_and_clean_kitchen(new_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe_name, variation_name)
        new_order_id_1 = rs.get_payload()
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
        output_string = rs.rc['message']
        self.assertTrue(new_order_id_1 in output_string)

        found_completed_serving = False
        wait_time = [.2, .5, .5, .5, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 10, 10]
        for wt in wait_time:
            rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
            output_string = rs.rc['message']
            n = output_string.count(new_order_id_1)
            if n == 2 and ('OrderRun Completed' in output_string):
                found_completed_serving = True
                break
            time.sleep(wt)
        self.assertTrue(found_completed_serving)
        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    def test_order_list_for_repeating_order(self):
        parent_kitchen = 'master'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name, repeater=True)
        new_kitchen = 'test_order_list_for_repeating_order'
        new_kitchen = self._add_my_guid(new_kitchen)
        self._delete_and_clean_kitchen(new_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe_name, variation_name)
        new_order_id_1 = rs.get_payload()
        self.assertTrue(rs.ok())

        found_completed_serving = False
        wait_time = [10,61,61,61,61]
        for wt in wait_time:
            rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
            output_string = rs.rc['message']
            n = output_string.count(new_order_id_1)
            if n >= 3 and ('OrderRun Completed' in output_string):
                found_completed_serving = True
                break
            time.sleep(wt)
        self.assertTrue(found_completed_serving)
        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    def test_order_list_with_filters(self):
        parent_kitchen = 'CLI-Top'
        # Don't use a guid for this. Don't
        kitchen = self._add_my_guid('test_order_list_with_filters')
        recipe1 = 'parallel-recipe-test'
        recipe1_variation = self._get_run_variation_for_recipe(recipe1)
        recipe2 = 'simple'
        recipe2_variation = 'simple-variation-now'

        setup = True
        if setup:
            self._delete_and_clean_kitchen(kitchen)
            rv = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, kitchen)
            self.assertTrue(rv.ok())

        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe1, recipe1_variation)
        self.assertTrue(rv.ok())
        first_order = rv.get_payload()
        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe1, recipe1_variation)
        self.assertTrue(rv.ok())

        time.sleep(20)

        rs = DKCloudCommandRunner.list_order(self._api, kitchen)
        self.assertTrue(rs.ok())
        message = rs.rc['message']
        self.assertTrue(
            'OrderRun is Planned' in message or 'OrderRun Completed' in message or 'OrderRun is Active' in message)

        # cleanup
        self._delete_and_clean_kitchen(kitchen)

    def test_orderrun_delete(self):
        mock_api = DKCloudAPIMock(self._cr_config)
        rs = DKCloudCommandRunner.delete_orderrun(mock_api, 'good')
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.delete_orderrun(mock_api, 'bad')
        self.assertFalse(rs.ok())

    def test_kitchen_config(self):
        parent_kitchen = 'CLI-Top'
        child_kitchen = self._add_my_guid('modify_kitchen_settings_runner')

        setup = True
        if setup:
            self._delete_and_clean_kitchen(child_kitchen)
            rv = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, child_kitchen)
            self.assertTrue(rv.ok())

        add = (('newvar1', 'newval1'),)
        unset = ('newvar1')
        get = ('newvar1')
        listall = True
        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, add=add)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue('newvar1 added' in message)

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, get=get)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue(message == 'newval1\n')

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, unset=unset)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, listall=listall)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue('newvar1' not in message)

        cleanup = False
        if cleanup:
            self._delete_and_clean_kitchen(child_kitchen)

    # helpers ---------------------------------
    def _delete_and_clean_kitchen(self, kitchen_name):
        DKCloudCommandRunner.delete_kitchen(self._api, kitchen_name)

    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(str(resp).find('diverged') < 0)

    def _get_recipe_file(self, kitchen, recipe_name, file_path, file_name, temp_dir=None):
        delete_temp_dir = td = False
        if temp_dir is None:
            td, kitchen_dir = self._make_kitchen_dir(kitchen, change_dir=False)
            delete_temp_dir = True
        else:
            kitchen_dir = temp_dir
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen, recipe_name, kitchen_dir)
        self.assertTrue(rs.ok())
        the_path = os.path.join(kitchen_dir, os.path.join(file_path, file_name))
        if os.path.isfile(the_path):
            with open(the_path, 'r') as rfile:
                rfile.seek(0)
                the_file = rfile.read()
            rc = the_file
        else:
            rc = None
        if delete_temp_dir is True:
            shutil.rmtree(td, ignore_errors=True)
        return rc

    def _get_recipe(self, kitchen, recipe):
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen, recipe)
        self.assertTrue(rs.ok())
        return True


if __name__ == '__main__':
    unittest.main()
