import unittest
import sys
import pickle
import os, tempfile, shutil
from DKCommonUnitTestSettings import DKCommonUnitTestSettings

from DKRecipeDisk import *
from DKKitchenDisk import *

__author__ = 'DataKitchen, Inc.'

"""
WHERE DOES THE TEST DATA COME FROM?
recipe.p comes from TestCloudAPI.py::test_get_recipe
with the two pickle lines un-commented.

./Recipes/dk/templates/simple is a copy of the recipe files
that recipe.p was generated from
"""


class TestDKRecipeDisk(DKCommonUnitTestSettings):

    def test_save_recipe_to_disk(self):

        r = pickle.load(open("recipe.p", "rb"))
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestDKRecipeDisk._TEMPFILE_LOCATION)
        kitchen_name = 'test_kitchen'
        DKKitchenDisk.write_kitchen(kitchen_name, temp_dir)
        kitchen_dir = os.path.join(temp_dir, kitchen_name)

        d = DKRecipeDisk(r['ORIG_HEAD'], r['recipes']['simple'], kitchen_dir)
        rc = d.save_recipe_to_disk()
        self.assertTrue(rc is not None)
        self.assertTrue(is_same(os.path.join(kitchen_dir, 'simple'),
                                os.path.join(os.getcwd(), 'Recipes/dk/templates/simple')), 'Pickled recipe differs from copy of recipe in Recipes')
        self.assertTrue(os.path.isfile(os.path.join(kitchen_dir, DK_DIR, 'recipes', 'simple', 'RECIPE_META')))
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_find_recipe(self):

        kitchen_name = 'bongo'
        temp_dir, kitchen_dir, kitchen_subdir, bad_dir = self._make_kitchen_testing_dir(kitchen_name)

        rv = DKRecipeDisk._find_recipe('snoozle')
        self.assertIsNone(rv)

        rv = DKRecipeDisk._find_recipe(kitchen_dir)
        self.assertIsNone(rv)

        rv = DKRecipeDisk._find_recipe(os.path.join(kitchen_dir, '.dk'))
        self.assertIsNone(rv)

        rv = DKRecipeDisk._find_recipe(temp_dir)
        self.assertIsNone(rv)

        recipe_root_path = os.path.join(kitchen_dir, 'recipe1')
        rv = DKRecipeDisk._find_recipe(recipe_root_path)
        self.assertEqual(rv, 'recipe1')

        node_path = os.path.join(recipe_root_path, 'node1')
        rv = DKRecipeDisk._find_recipe(node_path)
        self.assertEqual(rv, 'recipe1')

        datasources_path = os.path.join(node_path, 'data_sources')
        rv = DKRecipeDisk._find_recipe(datasources_path)
        self.assertEqual(rv, 'recipe1')

        rv = DKRecipeDisk._find_recipe(bad_dir)
        self.assertIsNone(rv)

        rv = DKRecipeDisk.is_recipe_root_dir(bad_dir)
        self.assertFalse(rv)

        rv = DKRecipeDisk.is_recipe_root_dir(node_path)
        self.assertFalse(rv)

        rv = DKRecipeDisk.is_recipe_root_dir(recipe_root_path)
        self.assertTrue(rv)

        rv = DKRecipeDisk.find_recipe_root_dir(bad_dir)
        self.assertIsNone(rv)
        rv = DKRecipeDisk.find_recipe_root_dir(node_path)
        self.assertEqual(rv, recipe_root_path)
        rv = DKRecipeDisk.find_recipe_root_dir(recipe_root_path)
        self.assertEqual(rv, recipe_root_path)

        recipe_meta_file_path = os.path.join(kitchen_dir, '.dk', 'recipes', 'recipe1', 'RECIPE_META')
        os.remove(recipe_meta_file_path)
        rv = DKRecipeDisk._find_recipe(os.path.join(kitchen_dir, 'recipe1'))
        self.assertIsNone(rv)

        shutil.rmtree(temp_dir)

    def test_compare_sha(self):
        recipe_info = pickle.load(open("recipe.p", "rb"))
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestDKRecipeDisk._TEMPFILE_LOCATION)
        kitchen_name = 'test_kitchen'
        DKKitchenDisk.write_kitchen(kitchen_name, temp_dir)
        kitchen_dir = os.path.join(temp_dir, kitchen_name)

        recipe = recipe_info['recipes']['simple']
        d = DKRecipeDisk(recipe_info['ORIG_HEAD'], recipe, kitchen_dir)
        rc = d.save_recipe_to_disk()
        self.assertTrue(rc is not None)

        # LOCAL CHANGES - Muck with both side to create differences
        local_sha_dir = os.path.join(kitchen_dir, 'simple')

        # Modify existing file
        with open(os.path.join(local_sha_dir, 'node1/description.json'), 'w') as f:
            f.write('BooGa BooGa')
        # Add a new file
        with open(os.path.join(local_sha_dir, 'node1/newfile.json'), 'w') as f:
            f.write('This is my new file. Hooray!')
        # Delete a file
        os.remove(os.path.join(local_sha_dir, 'node1/post_condition.json'))
        # Remove a directory
        shutil.rmtree(os.path.join(local_sha_dir, 'node1/data_sinks'))

        # "REMOTE" Changes
        # Change a sha
        recipe['simple/node2'][0]['sha'] = 'Who messed with my sha!'
        # Remove a remote file
        recipe['simple/node2'].pop()
        # Remove a directory
        del recipe['simple/node2/data_sinks']

        local_sha = get_directory_sha(local_sha_dir)
        rv = compare_sha(recipe, local_sha)
        same_count = 0
        for folder_name, folder_contents in rv['same'].iteritems():
            same_count += len(folder_contents)
        self.assertTrue(same_count >= 12)
        self.assertEqual(len(rv['different']), 2)

        only_local_count = 0
        for folder_name, folder_contents in rv['only_local'].iteritems():
            only_local_count += len(folder_contents)

        self.assertEqual(only_local_count, 2)
        self.assertEqual(len(rv['only_remote']), 2)

        shutil.rmtree(temp_dir)

    def test_flatten_tree(self):
        print 'hello'

    def test_build_sha1_directory(self):
        fp = os.path.join(os.getcwd(), 'files', 'recipe01')
        r = get_directory_sha(fp)
        self.assertIn('recipe01', r)
        self.assertIn('recipe01/sub01', r)
        self.assertIn('recipe01/sub01/sub02', r)
        sub02 = r['recipe01/sub01/sub02']
        sub01 = r['recipe01/sub01']
        root = r['recipe01']
        self.assertEqual(2, len(sub02))
        self.assertEqual(1, len(sub01))
        self.assertEqual(2, len(root))
        self.assertEqual(sub02[1]['filename'], 'file_01_01_02_02.txt')
        self.assertEqual(sub02[1]['sha'], '615487a0933769879c9114e38c45c6a55ed84f1d')
        self.assertEqual(sub01[0]['filename'], 'file_01_01_01.txt')
        self.assertEqual(sub01[0]['sha'], '3da4c3e0af822e6e38dcf9ac3772c10a283a388d')
        self.assertEqual(root[0]['filename'], 'file_01_01.txt')
        self.assertEqual(root[0]['sha'], 'c9536cbfeddf3b47bce62052c516550d742e6840')

    # <kitchen_name>
    #   .dk
    #       KITCHEN_META
    #   bad
    #       .dk
    #   kitchen_subdir
    #   recipe1
    #       node1
    def _make_kitchen_testing_dir(self, kitchen_name):
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestDKRecipeDisk._TEMPFILE_LOCATION)
        kitchen_dir = os.path.join(temp_dir, kitchen_name)
        os.mkdir(kitchen_dir)
        dot_dir = os.path.join(kitchen_dir, '.dk')
        os.mkdir(dot_dir)

        bad_dir = os.path.join(temp_dir, 'bad')
        os.mkdir(bad_dir)
        bad_dot_dir = os.path.join(bad_dir, '.dk')
        os.mkdir(bad_dot_dir)

        with open(os.path.join(dot_dir, 'KITCHEN_META'), 'w') as kitchen_file:
            kitchen_file.write(kitchen_name)

        kitchen_subdir = os.path.join(kitchen_dir, 'kitchen_subdir')
        os.mkdir(kitchen_subdir)


        # Recipes
        recipes_subdir = os.path.join(dot_dir, 'recipes')
        os.mkdir(recipes_subdir)

        recipe_subdir = os.path.join(recipes_subdir, 'recipe1')
        os.mkdir(recipe_subdir)

        with open(os.path.join(recipe_subdir, 'RECIPE_META'), 'w') as recipe_meta_file:
            recipe_meta_file.write('recipe1')

        recipe1_subdir = os.path.join(kitchen_dir, 'recipe1')
        os.mkdir(recipe1_subdir)

        node1_subdir = os.path.join(recipe1_subdir, 'node1')
        os.mkdir(node1_subdir)

        ds_subdir = os.path.join(node1_subdir, 'data_sources')
        os.mkdir(ds_subdir)

        return temp_dir, kitchen_dir, kitchen_subdir, bad_dir

    def test_find_kitchen(self):

        kitchen_name = 'bobo'
        temp_dir, kitchen_dir, kitchen_subdir, bad_dir = self._make_kitchen_testing_dir(kitchen_name)

        self.assertIsNone(DKKitchenDisk.find_kitchen_name(temp_dir))
        self.assertEqual(DKKitchenDisk.find_kitchen_name(kitchen_dir), kitchen_name)
        self.assertEqual(DKKitchenDisk.find_kitchen_name(kitchen_subdir), kitchen_name)
        self.assertIsNone(DKKitchenDisk.find_kitchen_name(bad_dir))

        shutil.rmtree(temp_dir)

    def test_find_kitchen_meta_dir(self):

        kitchen_name = 'bobo'
        temp_dir, kitchen_dir, kitchen_subdir, bad_dir = self._make_kitchen_testing_dir(kitchen_name)

        kitchen_meta_dir = os.path.join(temp_dir, kitchen_name, DK_DIR)
        self.assertIsNone(DKKitchenDisk.find_kitchen_meta_dir(temp_dir))
        self.assertEqual(DKKitchenDisk.find_kitchen_meta_dir(kitchen_dir), kitchen_meta_dir)
        self.assertEqual(DKKitchenDisk.find_kitchen_meta_dir(kitchen_subdir), kitchen_meta_dir)
        self.assertIsNone(DKKitchenDisk.find_kitchen_meta_dir(bad_dir))

    def test_find_kitchen_root_dir(self):
        kitchen_name = 'bobo'
        temp_dir, kitchen_dir, kitchen_subdir, bad_dir = self._make_kitchen_testing_dir(kitchen_name)
        self.assertIsNone(DKKitchenDisk.find_kitchen_root_dir(temp_dir))
        self.assertEqual(DKKitchenDisk.find_kitchen_root_dir(kitchen_dir), kitchen_dir)
        self.assertEqual(DKKitchenDisk.find_kitchen_root_dir(kitchen_subdir), kitchen_dir)
        self.assertIsNone(DKKitchenDisk.find_kitchen_root_dir(bad_dir))

    def test_is_kitchen_root_dir(self):
        kitchen_name = 'bobo'
        temp_dir, kitchen_dir, kitchen_subdir, bad_dir = self._make_kitchen_testing_dir(kitchen_name)
        self.assertFalse(DKKitchenDisk.is_kitchen_root_dir(temp_dir))
        self.assertTrue(DKKitchenDisk.is_kitchen_root_dir(kitchen_dir))
        self.assertFalse(DKKitchenDisk.is_kitchen_root_dir(kitchen_subdir))
        self.assertFalse(DKKitchenDisk.is_kitchen_root_dir(bad_dir))


if __name__ == '__main__':
    unittest.main()
