import unittest
from sys import path
import datetime
import json
import time
import hashlib
import tempfile
import pprint

import base64
import os, shutil
from collections import OrderedDict

from BaseTestCloud import BaseTestCloud
from DKCloudAPI import DKCloudAPI
from DKCloudCommandRunner import DKCloudCommandRunner


class TestCloudAPI(BaseTestCloud):
    def test_a_list_kitchen(self):
        # setup
        name = 'kitchens-plus'
        # test
        kitchens = self._list_kitchens()
        self.assertIsNotNone(kitchens)
        found = False
        for kitchen in kitchens:
            if isinstance(kitchen, dict) is True and 'name' in kitchen and name == kitchen['name']:
                found = True
        self.assertTrue(found)
        # cleanup (none)

    def test_create_kitchen(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'temp-volatile-kitchen-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        # test
        self._delete_kitchen(new_kitchen)  # clean up junk
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc)
        kitchens = self._list_kitchens()
        found = False
        for kitchen in kitchens:
            if isinstance(kitchen, dict) is True and 'name' in kitchen and new_kitchen == kitchen['name']:
                found = True
        self.assertTrue(found)
        # cleanup
        rc = self._delete_kitchen(new_kitchen)
        self.assertTrue(rc)

    def test_delete_kitchen(self):
        # setup
        parent_kitchen = 'CLI-Top'
        del_kitchen = 'temp-fleeting-kitchen-API'
        del_kitchen = self._add_my_guid(del_kitchen)
        self._delete_kitchen(del_kitchen)  # clean up junk
        rc = self._create_kitchen(parent_kitchen, del_kitchen)
        self.assertTrue(rc)
        # test
        rc = self._delete_kitchen(del_kitchen)
        self.assertTrue(rc)
        kitchens = self._list_kitchens()
        found = False
        for kitchen in kitchens:
            if isinstance(kitchen, dict) is True and 'name' in kitchen and del_kitchen == kitchen['name']:
                found = True
        self.assertFalse(found)
        # cleanup (none)

    def test_update_kitchen(self):
        update_kitchen_name = self._branch
        original_description = 'example description'
        update_description = '%s %s' % (original_description, 'command line test')
        # setup
        update_kitchen = self._get_kitchen_dict(update_kitchen_name)
        self.assertIsNotNone(update_kitchen)
        update_kitchen['description'] = update_description
        # test
        self.assertTrue(self._api.update_kitchen(update_kitchen, 'command line test 2'))

        if self._use_mock is False:
            updated_kitchen = self._get_kitchen_dict(update_kitchen_name)
            self.assertTrue('description' in updated_kitchen)
            self.assertTrue(updated_kitchen['description'] == update_description)
            updated_kitchen['description'] = original_description
            self.assertTrue(self._api.update_kitchen(updated_kitchen, 'command line test 2'))

    def test_list_recipe(self):
        # setup
        kitchen = 'CLI-Top'
        recipe_name = 'simple'
        # test
        recipe_names = self._list_recipe(kitchen)
        self.assertIsNotNone(recipe_names)
        my_recipe = next(recipe for recipe in recipe_names if recipe == recipe_name)
        self.assertIsNotNone(my_recipe)  # should get back a list of strings
        # cleanup (none)

    def test_get_recipe(self):
        # setup
        kitchen = 'CLI-Top'
        recipe = 'simple'

        # How do we handle a non-existent recipe?
        bad_recipe = "momo"
        rs = self._api.get_recipe(kitchen, bad_recipe)
        self.assertFalse(rs.ok())

        # test
        rs = self._get_recipe(kitchen, recipe)
        self.assertIsNotNone(rs)
        # save recipe for use in DKRecipeDisk.py unit tests
        if True:
            import pickle
            pickle.dump(rs, open("recipe.p", "wb"))
        found = False
        for r in rs:
            if isinstance(r, unicode):
                found = True
        self.assertTrue(found)  # should get back a list of strings

        # cleanup (none)

    def test_recipe_status(self):
        # setup
        kitchen = 'CLI-Top'
        recipe = 'simple'

        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen, change_dir=True)

        start_time = time.time()
        rv = DKCloudCommandRunner.get_recipe(self._api, kitchen, recipe)
        elapsed_recipe_status = time.time() - start_time
        print 'get_recipe - elapsed: %d' % elapsed_recipe_status

        new_path = os.path.join(kitchen_dir, recipe)
        os.chdir(new_path)

        new_file_path = os.path.join(new_path, 'new_file.txt')
        with open(new_file_path, 'w') as new_file:
            new_file.write('this is my new contents')
            new_file.flush()

        new_dir_path = os.path.join(new_path, 'newsubdir')
        os.makedirs(new_dir_path)

        new_sub_file_path = os.path.join(new_dir_path, 'new_sub_file.txt')
        with open(new_sub_file_path, 'w') as new_file:
            new_file.write('this is my new contents in my sub file')
            new_file.flush()

        newsubdir2 = os.path.join(new_path, 'newsubdir2')
        os.makedirs(newsubdir2)

        newsubsubdir = os.path.join(newsubdir2, 'newsubsubdir')
        os.makedirs(newsubsubdir)

        new_file_in_subsubdir = os.path.join(newsubsubdir, 'new-subsubdir-file.txt')
        with open(new_file_in_subsubdir, 'w') as new_file_in_subsubdir_file:
            new_file_in_subsubdir_file.write('{\n\t"animal":"cat",\n\t"color":"blue"\n}')
            new_file_in_subsubdir_file.flush()

        variables = os.path.join(new_path, 'variables.json')
        os.remove(variables)

        source_path = os.path.join(new_path, 'node2/data_sources/DKDataSource_NoOp.json')
        with open(source_path, 'a') as source_file:
            source_file.write("I'm adding some text to this file")
            source_file.flush()

        node1 = os.path.join(new_path, 'node1')
        shutil.rmtree(node1)

        start_time = time.time()
        rc = self._api.recipe_status(kitchen, recipe)
        elapsed_recipe_status = time.time() - start_time
        print 'recipe_status - elapsed: %d' % elapsed_recipe_status
        self.assertTrue(rc.ok())
        rv = rc.get_payload()
        self.assertEqual(len(rv['different']), 1)
        self.assertEqual(len(rv['only_remote']), 4)
        self.assertEqual(len(rv['only_local']), 4)
        self.assertEqual(len(rv['same']), 5)
        self.assertEqual(len(rv['same']['simple/node2']), 4)
        shutil.rmtree(temp_dir)

    def test_path_sorting(self):

        paths = ['description.json', 'graph.json', 'simple-file.txt', 'variables.json', 'variations.json', 'node2/data_sinks', 'node1/data_sinks', 'node2', 'node1', 'node1/data_sources', 'resources', 'node2/data_sources']
        paths = ['simple/newsubdir', 'simple/new_file.txt', 'simple/newsubdir2', 'simple/newsubdir2/newsubsubdir']
        paths_sorted = sorted(paths)
        for idx, path in enumerate(paths_sorted):
            dir = os.path.dirname(os.path.commonprefix(paths))
        print dir

    def test_update_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_update_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        file_name = 'description.json'
        api_file_key = file_name
        message = 'test update CLI-test_update_file'
        update_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        self._delete_kitchen(test_kitchen)

        original_file = self._get_recipe_file(parent_kitchen, recipe_name, file_name, DKCloudAPI.JSON)
        self.assertTrue(self._create_kitchen(parent_kitchen, test_kitchen))
        new_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, file_name, DKCloudAPI.JSON)
        self.assertEqual(original_file, new_kitchen_file)
        new_kitchen_file_dict = self._get_the_dict(new_kitchen_file)

        # test
        new_kitchen_file_dict[test_kitchen] = update_str
        new_kitchen_file2 = self._get_the_json_str(new_kitchen_file_dict)
        rv = self._api.update_file(test_kitchen, recipe_name, message, api_file_key, new_kitchen_file2)
        self.assertTrue(rv.ok())
        new_kitchen_file3 = self._get_recipe_file(test_kitchen, recipe_name, file_name, DKCloudAPI.JSON)
        self.assertEqual(new_kitchen_file2, new_kitchen_file3)

        # cleanup (none)
        self.assertTrue(self._delete_kitchen(test_kitchen))

    def test_add_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'test_create_file-API'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        file_name = 'added.sql'
        filedir = 'resources'
        recipe_file_key = os.path.join(recipe_name, filedir)
        file_contents = '--\n-- sql for you\n--\n\nselect 1024\n\n'
        file_path = os.path.join(filedir, file_name)
        message = 'test update test_create_file-API'
        self._delete_kitchen(test_kitchen)
        self.assertTrue(self._create_kitchen(parent_kitchen, test_kitchen))
        # test
        rv = self._api.add_file(test_kitchen, recipe_name, message, file_path, file_contents)
        self.assertTrue(rv, "API add file failed")

        new_file = self._get_recipe_file_full(test_kitchen, recipe_name, recipe_file_key, file_name, DKCloudAPI.TEXT,
                                              check=False)
        self.assertTrue(new_file is not None)
        self.assertEqual(file_contents, new_file)
        # cleanup
        self._delete_kitchen(test_kitchen)

    def test_delete_file_top1(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'test_delete_file_top1-API'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        file_name = 'description.json'
        recipe_file_key = file_name
        message = 'test update test_delete_file_top1-API'
        self._delete_kitchen(test_kitchen)  # make sure it is gone
        self.assertTrue(self._create_kitchen(parent_kitchen, test_kitchen))
        # test
        rv = self._api.delete_file(test_kitchen, recipe_name, message, recipe_file_key, file_name)
        self.assertTrue(rv.ok())
        gone_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, file_name, DKCloudAPI.JSON, check=False)
        self.assertTrue(gone_kitchen_file is None)
        # cleanup
        self._delete_kitchen(test_kitchen)

    def test_delete_file_deeper(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'test_delete_file_deeper-API'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        filedir = 'resources'
        file_name = 'very_cool.sql'
        api_file_key = os.path.join(filedir, file_name)
        recipe_file_key = os.path.join(recipe_name, filedir)
        message = 'test update test_delete_file_deeper-API'
        self._delete_kitchen(test_kitchen)
        self.assertTrue(self._create_kitchen(parent_kitchen, test_kitchen))
        # test
        rv = self._api.delete_file(test_kitchen, recipe_name, message, api_file_key, file_name)
        self.assertTrue(rv.ok())

        gone_kitchen_file = self._get_recipe_file_full(test_kitchen, recipe_name, recipe_file_key,
                                                       file_name, 'text', False)
        self.assertTrue(gone_kitchen_file is None)
        # cleanup
        self._delete_kitchen(test_kitchen)

        # def test_cook_recipe(self):
        #     # setup
        #     kitchen = 'CLI-Top'
        #     recipe = 'simple'
        #     variation = 'simple-variation-now'
        #     # test
        #     rs = self._cook_recipe(kitchen, recipe, variation)
        #     self.assertIsNotNone(rs)
        #     self.assertTrue(rs == u'success')
        #     pass
        #     # cleanup (none)

    # --------------------------------------------------------------------------------------------------------------------
    #  Order commands
    # --------------------------------------------------------------------------------------------------------------------

    def test_create_order(self):
        # setup
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = 'simple-variation-now'
        # test
        rs = self._create_order(kitchen, recipe, variation)
        self.assertIsNotNone(rs)
        self.assertTrue('simple' in rs)
        pass
        # cleanup (none)

    def test_create_order_one_node(self):
        # setup
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = 'simple-variation-now'
        node = 'node2'
        # test
        rs = self._create_order(kitchen, recipe, variation, node)
        self.assertIsNotNone(rs)
        self.assertTrue('simple' in rs)
        pass

    def test_delete_all_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderAPI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        self._delete_kitchen(new_kitchen)  # clean up junk
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc)
        order_id = self._create_order(new_kitchen, recipe, variation)
        self.assertIsNotNone(order_id)
        self.assertTrue('simple' in order_id)
        # test
        rc = self._order_delete_all(new_kitchen)
        # cleanup
        rc = self._delete_kitchen(new_kitchen)
        self.assertTrue(rc)

    def test_delete_one_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_delete_one_order-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        self._delete_kitchen(new_kitchen)  # clean up junk
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc)
        order_id = self._create_order(new_kitchen, recipe, variation)
        self.assertIsNotNone(order_id)
        self.assertTrue('simple' in order_id)
        # test
        rc = self._order_delete_one(order_id)
        # cleanup
        rc = self._delete_kitchen(new_kitchen)
        self.assertTrue(rc)

    def test_order_stop(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_order_stop-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'test-everything-recipe'
        variation = self._get_run_variation_for_recipe('test-everything-recipe')
        self._delete_kitchen(new_kitchen)  # clean up junk
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc)
        order_id = self._create_order(new_kitchen, recipe, variation)
        self.assertIsNotNone(order_id)
        # self.assertTrue('simple' in order_id)
        # test
        time.sleep(2)
        rc = self._order_stop(order_id)
        # cleanup
        rc = self._delete_kitchen(new_kitchen)
        self.assertTrue(rc)

    def test_orderrun_stop(self):
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_orderrun_stop-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)

        self._delete_kitchen(new_kitchen)
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())

        # test
        new_order_id = self._create_order(new_kitchen, recipe_name, variation_name)
        self.assertIsNotNone(new_order_id)

        # order should be available immediately
        rc = self._api.list_order(new_kitchen)
        self.assertTrue(rc.ok())
        order_stuff = rc.get_payload()
        self.assertTrue('orders' in order_stuff)
        self.assertTrue('servings' in order_stuff)
        found_order = next((order for order in order_stuff['orders'] if order['serving_chronos_id'] == new_order_id),
                           None)
        self.assertIsNotNone(found_order)

        # wait a few seconds for the serving

        wait_time = [.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        for wt in wait_time:
            rc = self._api.list_order(new_kitchen)
            self.assertTrue(rc.ok())
            order_stuff = rc.get_payload()
            self.assertTrue('servings' in order_stuff)
            found_serving = next(
                    (serving for serving in order_stuff['servings'] if serving['serving_chronos_id'] == new_order_id),
                    None)
            if found_serving is not None:
                break
            time.sleep(wt)
        self.assertIsNotNone(found_serving)
        orderrun_id = found_serving['serving_mesos_id']
        rc2 = self._orderrun_stop(orderrun_id)
        self.assertTrue(rc2.ok())
        # cleanup
        self._delete_kitchen(new_kitchen)

    def test_get_compiled_serving_from_recipe(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_get_compiled_serving_from_recipe-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = 'variation-test'
        self._delete_kitchen(new_kitchen)
        self.assertTrue(self._create_kitchen(parent_kitchen, new_kitchen))
        # test
        resp = self._get_compiled_serving(parent_kitchen, recipe_name, variation_name)
        self.assertTrue(isinstance(resp, dict))
        found = False
        for rn, recipe in resp.iteritems():
            if rn == recipe_name:
                found = True
        self.assertTrue(found)
        self.assertTrue(isinstance(resp, dict))
        self.assertTrue(len(resp) == 28)
        self.assertTrue(len(resp[recipe_name]) == 5)
        self.assertTrue(isinstance(resp[recipe_name], list))
        found_desc = False
        for item in resp[recipe_name]:
            if 'filename' in item and 'json' in item and item['filename'] == 'description.json':
                found_desc = True
                self.assertTrue(len(item['json']) >= 1)
        self.assertTrue(found_desc)
        # cleanup
        self._delete_kitchen(new_kitchen)

    def test_merge_kitchens_success(self):
        existing_kitchen_name = 'CLI-Top'
        base_test_kitchen_name = 'base-test-kitchen'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = 'branched-from-base-test-kitchen'
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)

        # setup
        self._delete_kitchen(branched_test_kitchen_name)
        self._delete_kitchen(base_test_kitchen_name)
        # test
        # create base kitchen
        self.assertTrue(self._create_kitchen(existing_kitchen_name, base_test_kitchen_name))
        # create branch kitchen from base kitchen
        self.assertTrue(self._create_kitchen(base_test_kitchen_name, branched_test_kitchen_name))
        # do merge
        rd = self._merge_kitchens(branched_test_kitchen_name, base_test_kitchen_name)
        self._check_no_merge_conflicts(rd)

        rd = self._merge_kitchens(base_test_kitchen_name, branched_test_kitchen_name)
        self._check_no_merge_conflicts(rd)

        # cleanup
        self._delete_kitchen(branched_test_kitchen_name)
        self._delete_kitchen(base_test_kitchen_name)

    def test_merge_kitchens_improved(self):
        existing_kitchen_name = 'CLI-Top'
        recipe = 'simple'
        parent_kitchen = 'merge-parent'
        parent_kitchen = self._add_my_guid(parent_kitchen)
        child_kitchen = 'merge-child'
        child_kitchen = self._add_my_guid(child_kitchen)

        setup = True
        cleanup = True

        conflict_file = 'conflicted-file.txt'
        if setup:
            # # setup
            self._delete_kitchen(parent_kitchen)
            self._delete_kitchen(child_kitchen)
            self.assertTrue(self._create_kitchen(existing_kitchen_name, parent_kitchen))
            rv = self._api.add_file(parent_kitchen, recipe, 'File will be changed on both branches to create a conflict.', conflict_file, 'top\nbottom\n')
            self.assertTrue(rv.ok())

            self.assertTrue(self._create_kitchen(parent_kitchen, child_kitchen))
            rv = self._api.update_file(child_kitchen, recipe, 'Changes on child to cause conflict', conflict_file, 'top\nchild\nbottom\n')
            self.assertTrue(rv.ok())

            rv = self._api.update_file(child_kitchen, recipe, 'Changes on parent to cause conflict', conflict_file, 'top\nparent\nbottom\n')
            self.assertTrue(rv.ok())

        # do merge
        rd = self._api.merge_kitchens_improved(child_kitchen, parent_kitchen)
        self.assertTrue(rd.ok())
        self.assertTrue(isinstance(rd.get_payload(), dict))
        self.assertTrue(rd.get_payload()['merge-kitchen-result']['status'] == 'success')
        merge_info = rd.get_payload()['merge-kitchen-result']['merge_info']
        self.assertTrue(merge_info['recipes']['simple']['simple'][0]['filename'] == 'conflicted-file.txt')
        self.assertTrue(merge_info['recipes']['simple']['simple'][0]['status'] == 'modified')

        if True:
            import pickle
            pickle.dump(rd, open("files/merge_kitchens_improved_success.p", "wb"))

        # cleanup
        if cleanup:
            self._delete_kitchen(child_kitchen)
            self._delete_kitchen(parent_kitchen)

    def test_merge_kitchens_improved_conflicts(self):
        existing_kitchen_name = 'CLI-Top'
        recipe = 'simple'
        parent_kitchen = 'merge-parent'
        parent_kitchen = self._add_my_guid(parent_kitchen)
        child_kitchen = 'merge-child'
        child_kitchen = self._add_my_guid(child_kitchen)

        setup = True
        cleanup = True
        conflict_file = 'conflicted-file.txt'
        if setup:
            # # setup
            self._delete_kitchen(parent_kitchen)
            self._delete_kitchen(child_kitchen)
            self.assertTrue(self._create_kitchen(existing_kitchen_name, parent_kitchen))
            rv = self._api.add_file(parent_kitchen, recipe,
                                       'File will be changed on both branches to create a conflict.', conflict_file,
                                       'top\nbottom\n')
            self.assertTrue(rv.ok())

            self.assertTrue(self._create_kitchen(parent_kitchen, child_kitchen))
            rv = self._api.update_file(child_kitchen, recipe, 'Changes on child to cause conflict', conflict_file,
                                       'top\nchild\nbottom\n')
            self.assertTrue(rv.ok())

            rv = self._api.update_file(parent_kitchen, recipe, 'Changes on parent to cause conflict', conflict_file,
                                       'top\nparent\nbottom\n')
            self.assertTrue(rv.ok())

        # do merge
        rd = self._api.merge_kitchens_improved(child_kitchen, parent_kitchen)
        self.assertTrue(rd.ok())
        payload = rd.get_payload()
        self.assertTrue(isinstance(payload, dict))
        self.assertTrue('conflicts' == rd.get_payload()['merge-kitchen-result']['status'])

        merge_info = rd.get_payload()['merge-kitchen-result']['merge_info']
        self.assertEqual(len(merge_info['conflicts']), 1)
        conflicts = merge_info['conflicts']
        self.assertTrue('>>>>>>>' in base64.b64decode(conflicts['simple']['simple'][0]['conflict_tags']))
        if True:
            import pickle
            pickle.dump(rd, open("files/merge_kitchens_improved_conflicts.p", "wb"))

        # cleanup
        if cleanup:
            self._delete_kitchen(child_kitchen)
            self._delete_kitchen(parent_kitchen)

    def test_merge_kitchens_1_fail(self):
        existing_kitchen_name = 'CLI-Top'
        base_test_kitchen_name = 'base-test-kitchen-API'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = 'branched-from-base-test-kitchen-API'
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)
        recipe_name = 'parallel-recipe-test'
        rpath = recipe_name
        file_name = 'description.json'
        recipe_file_key = file_name
        message = 'test update from test_merge_kitchens_fail'

        setup = True
        cleanup = True
        if setup:
            # setup
            self._delete_kitchen(branched_test_kitchen_name)
            self._delete_kitchen(base_test_kitchen_name)
            # test
            # create base kitchen
            self.assertTrue(self._create_kitchen(existing_kitchen_name, base_test_kitchen_name))
            self.assertTrue(self._create_kitchen(base_test_kitchen_name, branched_test_kitchen_name))
            base_test_kitchen_dict = OrderedDict()
            base_test_kitchen_dict['test_data'] = 'TIS SHOLD CONFICT'
            rc = self._api.update_file(base_test_kitchen_name, recipe_name, message,
                                       recipe_file_key, self._get_the_json_str(base_test_kitchen_dict))
            self.assertTrue(rc.ok())
            # do update of file
            new_kitchen_file_dict = OrderedDict()
            new_kitchen_file_dict['test_data'] = 'THIS SHOULD CONFLICT'
            rc = self._api.update_file(branched_test_kitchen_name, recipe_name,
                                       message + ' version2', recipe_file_key,
                                       self._get_the_json_str(new_kitchen_file_dict))
            self.assertTrue(rc.ok())
            # do merge
            rd = self._merge_kitchens(branched_test_kitchen_name, base_test_kitchen_name)
            # save merge conflicts for use in unit tests
            if True:
                import pickle
                pickle.dump(rd, open("files/merge_conflicts_1_file.p", "wb"))
            self._check_merge_conflicts(rd, recipe_name, rpath, file_name,
                                        branched_test_kitchen_name, base_test_kitchen_name)

        # Resolve the conflicts
        d2 = dict()
        d2[recipe_name] = {}
        d2[recipe_name][recipe_name] = {}
        conflict_key = '%s|%s|%s|%s|%s' % (branched_test_kitchen_name, base_test_kitchen_name, recipe_name, recipe_name,
                                           file_name)
        d2[recipe_name][recipe_name][conflict_key] = {'from_kitchen': branched_test_kitchen_name,
                                                                            'to_kitchen': base_test_kitchen_name,
                                                                            'recipe': recipe_name,
                                                                            'filename': file_name,
                                                                            'contents': 'THIS SHOULD CONFLICT'}
        rc = self._api.merge_kitchens_improved(branched_test_kitchen_name, base_test_kitchen_name, d2)
        self.assertTrue(rc.ok())
        self.assertTrue(isinstance(rc.get_payload(), dict))
        payload = rc.get_payload()
        self._check_no_merge_conflicts(payload)

        # cleanup
        if cleanup:
            self._delete_kitchen(branched_test_kitchen_name)
            self._delete_kitchen(base_test_kitchen_name)

    def test_merge_kitchens_multi_fail(self):
        # make different updates in 2 recipes, 1 file in simple, 2 files in parallel-recipe-test
        # 1. parallel-recipe-test/description.json
        # 2. parallel-recipe-test/node1/data_sources/DKDataSource_NoOp.json
        # 3. simple/resources/very_cool.sql

        existing_kitchen_name = 'CLI-Top'
        child_test_kitchen_name = 'child-test-kitchen-API'
        grandchild_test_kitchen_name = 'grandchild-test-kitchen-API'

        message = 'update message for file %d'

        recipe_a_name = 'parallel-recipe-test'
        recipe_b_name = 'simple'

        file_name1 = 'description.json'
        file_name2 = 'DKDataSource_NoOp.json'
        file_name3 = 'very_cool.sql'

        recipe_a_api_file1_key = file_name1
        recipe_a_api_file2_key = 'node1/data_sources/' + file_name2
        recipe_b_api_file3_key = 'resources/' + file_name3

        recipe_file_key1 = recipe_a_name
        recipe_file_key2 = recipe_a_name + '/node1/data_sources'
        recipe_file_key3 = recipe_b_name + '/resources'

        # setup
        self._delete_kitchen(grandchild_test_kitchen_name)
        self._delete_kitchen(child_test_kitchen_name)
        # test
        # create kitchens
        self.assertTrue(self._create_kitchen(existing_kitchen_name, child_test_kitchen_name))
        self.assertTrue(self._create_kitchen(child_test_kitchen_name, grandchild_test_kitchen_name))

        # FYI Cannot cook these updated recipes

        # update file 1
        self.assertTrue(self._api.update_file(child_test_kitchen_name, recipe_a_name, message % 1,
                                              recipe_a_api_file1_key, 'Kitchen Child Recipe A File 1\n').ok())
        self.assertTrue(self._api.update_file(grandchild_test_kitchen_name, recipe_a_name, message % 1,
                                              recipe_a_api_file1_key, 'Kitchen Grandchild Recipe A File 1\n').ok())

        # update file 2
        self.assertTrue(self._api.update_file(child_test_kitchen_name, recipe_a_name, message % 2,
                                              recipe_a_api_file2_key, 'Kitchen Child Recipe A File 2\n').ok())
        self.assertTrue(self._api.update_file(grandchild_test_kitchen_name, recipe_a_name, message % 2,
                                              recipe_a_api_file2_key, 'Kitchen Grandchild Recipe A File 2\n').ok())
        # update file 3
        self.assertTrue(self._api.update_file(child_test_kitchen_name, recipe_b_name, message % 3,
                                              recipe_b_api_file3_key, 'Kitchen Child Recipe B File 3\n').ok())
        self.assertTrue(self._api.update_file(grandchild_test_kitchen_name, recipe_b_name, message % 3,
                                              recipe_b_api_file3_key, 'Kitchen Grandchild Recipe B File 3\n').ok())

        # do merge
        rd = self._merge_kitchens(grandchild_test_kitchen_name, child_test_kitchen_name)
        # save merge conflicts for use in unit tests
        if True:
            import pickle
            pickle.dump(rd, open("files/merge_conflicts_multi_file.p", "wb"))

        self._check_merge_conflicts(rd, recipe_a_name, recipe_file_key1, file_name1,
                                    grandchild_test_kitchen_name, child_test_kitchen_name)
        self._check_merge_conflicts(rd, recipe_a_name, recipe_file_key2, file_name2,
                                    grandchild_test_kitchen_name, child_test_kitchen_name)
        self._check_merge_conflicts(rd, recipe_b_name, recipe_file_key3, file_name3,
                                    grandchild_test_kitchen_name, child_test_kitchen_name)

        # cleanup
        self._delete_kitchen(grandchild_test_kitchen_name)
        self._delete_kitchen(child_test_kitchen_name)

    def test_list_order_errors(self):
        bad_kitchen = 'bsdfdfsdlomobo'
        rc = self._api.list_order(bad_kitchen)
        self.assertTrue(rc.ok())
        order_stuff = rc.get_payload()
        self.assertIsNotNone(len(order_stuff['orders']) == 0)

    def test_list_order_quick(self):
        test_kitchen = 'CLI-Top'
        # order should be available immediately
        rc = self._api.list_order(test_kitchen)
        self.assertTrue(rc.ok())
        order_stuff = rc.get_payload()
        self.assertTrue('orders' in order_stuff)
        self.assertTrue('servings' in order_stuff)

    def test_list_order(self):
        parent_kitchen = 'master'
        new_kitchen = self._add_my_guid('test_order_status')
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)

        self._delete_kitchen(new_kitchen)
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())

        # test
        new_order_id = self._create_order(new_kitchen, recipe_name, variation_name)
        self.assertIsNotNone(new_order_id)

        # order should be available immediately
        rc = self._api.list_order(new_kitchen)
        self.assertTrue(rc.ok())
        order_stuff = rc.get_payload()
        self.assertTrue('orders' in order_stuff)
        self.assertTrue('servings' in order_stuff)
        found_order = next((order for order in order_stuff['orders'] if order['serving_chronos_id'] == new_order_id),
                           None)
        self.assertIsNotNone(found_order)

        # wait a few seconds for the serving
        found_serving = None
        wait_time = [.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 6, 6, 6, 6, 10]
        for wt in wait_time:
            rc = self._api.list_order(new_kitchen)
            self.assertTrue(rc.ok())
            order_stuff = rc.get_payload()
            self.assertTrue('servings' in order_stuff)
            found_serving = next(
                    (serving for serving in order_stuff['servings'] if serving['serving_chronos_id'] == new_order_id),
                    None)
            if found_serving is not None:
                break
            time.sleep(wt)
        self.assertIsNotNone(found_serving)
        self._delete_kitchen(new_kitchen)

    def test_orderrun_delete(self):
        parent_kitchen = 'master'
        new_kitchen = 'test_orderrun_delete'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)

        self._delete_kitchen(new_kitchen)
        # @todo add a delete all to the orders for this kitchen
        rc = self._create_kitchen(parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())

        # test
        new_order_id = self._create_order(new_kitchen, recipe_name, variation_name)
        self.assertIsNotNone(new_order_id)
        found_serving = None
        # wait a few seconds for the serving
        wait_time = [.5, 1, 1, 1, 2, 2, 2, 4, 4, 4, 4, 4]
        for wt in wait_time:
            rc = self._api.list_order(new_kitchen)
            self.assertTrue(rc.ok())
            order_stuff = rc.get_payload()
            print '%i got %s' % (wt, order_stuff)
            self.assertTrue('servings' in order_stuff)
            found_serving = next(
                    (serving for serving in order_stuff['servings'] if serving['serving_chronos_id'] == new_order_id),
                    None)
            if found_serving is not None:
                break
            time.sleep(wt)
        self.assertIsNotNone(found_serving)

        rv = self._api.delete_orderrun(found_serving['serving_mesos_id'])
        self.assertTrue(rv.ok())
        rv = self._api.delete_orderrun('bad_id')
        self.assertFalse(rv.ok())

        rc = self._api.list_order(new_kitchen)
        self.assertTrue(rc.ok())
        order_stuff = rc.get_payload()
        self.assertTrue('servings' in order_stuff)
        found_serving = next(
                (serving for serving in order_stuff['servings'] if serving['serving_chronos_id'] == new_order_id), None)
        self.assertIsNone(found_serving)
        self._delete_kitchen(new_kitchen)

    def test_kitchen_config(self):
        parent_kitchen = 'CLI-Top'
        child_kitchen = self._add_my_guid('modify_kitchen_settings_api')

        setup = True
        if setup:
            self._delete_kitchen(child_kitchen)
            self._create_kitchen(parent_kitchen, child_kitchen)

        add = (('newvar1', 'newval1'), ('newvar2', 'newval2'), ('newvar1', 'this should be in list'))
        rc = self._api.modify_kitchen_settings(child_kitchen, add=add)
        self.assertTrue(rc.ok())
        overrides_dict = rc.get_payload()
        newvar1 = next((var for var in overrides_dict if var['variable'] == 'newvar1'), None)
        self.assertIsNotNone(newvar1)
        self.assertTrue(newvar1['value'] == 'this should be in list')
        self.assertIsNotNone(next((var for var in overrides_dict if var['value'] == 'newval2'), None))

        add = (('newvarX', 'newval1'))
        rc = self._api.modify_kitchen_settings(child_kitchen, add=add)
        self.assertTrue(rc.ok())
        overrides_dict = rc.get_payload()
        newvar1 = next((var for var in overrides_dict if var['variable'] == 'newvar1'), None)
        self.assertIsNotNone(newvar1)
        self.assertTrue(newvar1['value'] == 'this should be in list')
        self.assertIsNotNone(next((var for var in overrides_dict if var['value'] == 'newval2'), None))

        unset = ('newvar1')
        rc = self._api.modify_kitchen_settings(child_kitchen, unset=unset)
        self.assertTrue(rc.ok())
        overrides_dict = rc.get_payload()
        self.assertIsNone(next((var for var in overrides_dict if var['variable'] == 'newvar1'), None))

        unset = ('newvar1', 'newvar2')
        rc = self._api.modify_kitchen_settings(child_kitchen, unset=unset)
        self.assertTrue(rc.ok())
        overrides_dict = rc.get_payload()
        self.assertIsNone(next((var for var in overrides_dict if var['variable'] == 'newvar1'), None))

        unset = ('doesnotexist')
        rc = self._api.modify_kitchen_settings(child_kitchen, unset=unset)
        self.assertTrue(rc.ok())
        overrides_dict = rc.get_payload()

        cleanup = True
        if cleanup:
            self._delete_kitchen(child_kitchen)

        # def config_kitchen(dk_api, kitchen, add, get, unset, listall):
    def test_kitchen_settings(self):
        kitchen_name = 'CLI-Top'
        rc = self._api.get_kitchen_settings(kitchen_name)
        self.assertTrue(rc.ok())
        kitchen_json = rc.get_payload()
        self.assertTrue('recipeoverrides' in kitchen_json)

    # helpers ---------------------------------
    # get the recipe from the server and return the file
    # WORKS JUST FOR THE top level files
    # TODO get rid of this routine because it only woks for the top level directory,
    # TODO switch to using _get_recipe_file_full()
    def _get_recipe_file(self, kitchen, recipe, file_name, the_type, check=True):
        the_file = None
        rs = self._get_recipe_files(kitchen, recipe)
        self.assertIsNotNone(rs)
        self.assertTrue(recipe in rs)
        self.assertIsNotNone(isinstance(rs[recipe], list))
        for item in rs[recipe]:  # JUST LOOKS IN TOP LEVEL DIRECTORY
            self.assertTrue(isinstance(item, dict))
            if DKCloudAPI.FILENAME in item and item[DKCloudAPI.FILENAME] == file_name and the_type in item:
                if isinstance(item[DKCloudAPI.JSON], dict):
                    the_file = json.dumps(item[DKCloudAPI.JSON])
                else:
                    the_file = item[DKCloudAPI.JSON]
        if check:
            self.assertIsNotNone(the_file)  # skip this e.g. looking for a deleted file
        return the_file

    def _get_recipe_file_full(self, kitchen, recipe, recipe_file_key, file_name, the_type, check=True):
        """
        :param kitchen:
        :param recipe:
        :param recipe_file_key: has the recipe name and the path to the file, but not the file
        :param file_name: just the file name
        :param the_type:
        :param check: set to false when you don't expect the file to be there
        :return:
        """
        the_file = None
        rs = self._get_recipe_files(kitchen, recipe)
        self.assertIsNotNone(rs)
        self.assertTrue(recipe in rs)
        self.assertIsNotNone(isinstance(rs[recipe], list))
        if recipe_file_key not in rs:
            return the_file
        for item in rs[recipe_file_key]:
            self.assertTrue(isinstance(item, dict))
            if DKCloudAPI.FILENAME in item and item[DKCloudAPI.FILENAME] == file_name and the_type in item:
                if the_type == DKCloudAPI.JSON:
                    if isinstance(item[DKCloudAPI.JSON], dict):
                        the_file = json.dumps(item[DKCloudAPI.JSON])
                    else:
                        the_file = item[DKCloudAPI.JSON]
                elif the_type == DKCloudAPI.TEXT:
                    the_file = item[DKCloudAPI.TEXT]
        if check:
            self.assertIsNotNone(the_file)  # skip this e.g. looking for a deleted file
        return the_file

    def _get_kitchen_dict(self, kitchen_name):
        return self._api.get_kitchen_dict(kitchen_name)

    def _delete_kitchen(self, kitchen, delete_servings=True):
        if delete_servings is True:
            self._api.order_delete_all(kitchen)
        return self._api.delete_kitchen(kitchen, 'junk')

    def _create_kitchen(self, existing_kitchen_name, new_kitchen_name):
        return self._api.create_kitchen(existing_kitchen_name, new_kitchen_name, 'junk')

    def _merge_kitchens(self, from_kitchen, to_kitchen, resolved_conflicts=None):
        rd = self._api.merge_kitchens_improved(from_kitchen, to_kitchen, resolved_conflicts)
        self.assertTrue(rd.ok())
        self.assertTrue(isinstance(rd.get_payload(), dict))
        return rd.get_payload()

    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(isinstance(resp, dict))
        self.assertTrue('merge-kitchen-result' in resp)
        self.assertTrue('status' in resp['merge-kitchen-result'])
        self.assertTrue(resp['merge-kitchen-result']['status'] == 'success')

    def _check_merge_conflicts(self, resp, recipe_name, recipe_path, conflict_file_name, from_kitchen_name,
                               to_kitchen_name):
        self.assertTrue(isinstance(resp, dict))
        self.assertTrue('merge-kitchen-result' in resp)

        conflicts = resp['merge-kitchen-result']['merge_info']['conflicts']

        self.assertTrue(recipe_name in conflicts)
        self.assertTrue('status' in resp['merge-kitchen-result'])
        self.assertTrue(resp['merge-kitchen-result']['status'] == 'conflicts')
        self.assertTrue(recipe_path in conflicts[recipe_name])
        self.assertTrue(isinstance(conflicts[recipe_name][recipe_path], list))
        for f in conflicts[recipe_name][recipe_path]:
            self.assertTrue(isinstance(f, dict))
            self.assertTrue('filename' in f)
            self.assertEqual(conflict_file_name, f['filename'])
        self.assertTrue('from-kitchen-name' in resp)
        self.assertEqual(resp['from-kitchen-name'], from_kitchen_name)
        self.assertTrue('to-kitchen-name' in resp)
        self.assertEqual(resp['to-kitchen-name'], to_kitchen_name)

    def _list_kitchens(self):
        rc = self._api.list_kitchen()
        self.assertTrue(rc.ok())
        kitchens = rc.get_payload()
        # test
        self.assertTrue(isinstance(kitchens, list))
        return kitchens

    def _list_recipe(self, kitchen):
        rs = self._api.list_recipe(kitchen)
        self.assertTrue(rs.ok)
        # test
        self.assertTrue(isinstance(rs.get_payload(), list))
        return rs.get_payload()

    def _get_recipe_files(self, kitchen, recipe):
        rs = self._api.get_recipe(kitchen, recipe)
        self.assertTrue(rs.ok())
        # test
        payload = rs.get_payload()
        self.assertTrue('recipes' in payload)
        self.assertTrue(isinstance(payload['recipes'], dict))
        return payload['recipes'][recipe]

    def _get_recipe(self, kitchen, recipe):
        rs = self._api.get_recipe(kitchen, recipe)
        self.assertTrue(rs.ok())
        # test
        payload = rs.get_payload()
        self.assertTrue('recipes' in payload)
        self.assertTrue('ORIG_HEAD' in payload)
        self.assertTrue(isinstance(payload['recipes'], dict))
        return payload

    def _create_order(self, kitchen, recipe, variation, node=None):
        rc = self._api.create_order(kitchen, recipe, variation, node)
        self.assertTrue(rc.ok())
        rs = rc.get_payload()
        self.assertTrue(isinstance(rs, basestring))
        return rs

    def _order_delete_all(self, kitchen):
        rc = self._api.order_delete_all(kitchen)
        self.assertTrue(rc.ok())
        return rc

    def _order_delete_one(self, order_id):
        rc = self._api.order_delete_one(order_id)
        self.assertTrue(rc.ok())
        return rc

    def _order_stop(self, order_id):
        rc = self._api.order_stop(order_id)
        self.assertTrue(rc.ok())
        return rc

    def _orderrun_stop(self, orderrun_id):
        rc = self._api.orderrun_stop(orderrun_id)
        self.assertTrue(rc.ok())
        return rc

    def _orderrun_detail(self, kitchen):
        rc = self._api.orderrun_detail(kitchen, dict())
        self.assertTrue(rc.ok())
        rs = rc.get_payload()
        self.assertTrue(isinstance(rs, list))
        return rs

    def _get_compiled_serving(self, kitchen, recipe_name, veriation_name):
        rd = self._api.get_compiled_serving(kitchen, recipe_name, veriation_name)
        self.assertTrue(rd.ok())
        p = rd.get_payload()
        return p


if __name__ == '__main__':
    unittest.main()
