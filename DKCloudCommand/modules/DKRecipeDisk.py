import os
import json
import filecmp
import glob
from githash import *
import re
import glob
from DKKitchenDisk import DKKitchenDisk
from DKIgnore import DKIgnore

# import os.path

# from sys import path
# from os.path import expanduser
# home = expanduser('~')  # does not end in a '/'
# if home + '/dev/DKModules/DKModules/' not in path:
#     path.insert(0, home + '/dev/DKModules/DKModules/')
# from DKSingletons import *

__author__ = 'DataKitchen, Inc.'

RECIPE_META = 'RECIPE_META'
DK_CONFLICTS_META = 'conflicts.json'
ORIG_HEAD = 'ORIG_HEAD'
IGNORED_FILES = ['.DS_Store', '.dk']

class DKRecipeDisk:
    def __init__(self, recipe_sha=None, recipe=None, path=None):
        self.recipe = recipe
        self._recipe_sha = recipe_sha
        self._recipe_path = path
        self._recipe_name = min(recipe.keys())

    # For  each recipe_file_key (key), file_list (value) in the dictionary
    #   if the directory exists
    #     delete it
    #   create the directory
    #   for each file in the file_list
    #     create the file
    #     write the contents
    #   write our metadata to the kitchen folder (.dk)
    def save_recipe_to_disk(self, update_meta=True):
        recipe_dict = self.recipe
        root_dir = self._recipe_path

        if isinstance(recipe_dict, dict) is False:
            return None
        if root_dir is None:
            return None

        if update_meta:
            if not self.write_recipe_meta(root_dir):
                return None

        for recipe_file_key, files_list in recipe_dict.iteritems():
            if len(recipe_file_key) > 0:
                full_dir = os.path.join(root_dir, recipe_file_key)
            else:
                return None
                # full_dir = root_dir  # original code, when does this happen?
            if os.path.isdir(full_dir) is False:
                try:
                    os.makedirs(full_dir)
                except Exception:
                    return None
            if isinstance(files_list, list) is False:
                return None
            for file_dict in files_list:
                if isinstance(file_dict, dict) is False:
                    return None
                self.write_files(full_dir, file_dict)
        return True

    def write_recipe_meta(self, start_dir):
        if not DKKitchenDisk.is_kitchen_root_dir(start_dir):
            print "'%s' is not a Kitchen directory" % start_dir
            return False

        kitchen_meta_dir = DKKitchenDisk.find_kitchen_meta_dir(start_dir)
        if kitchen_meta_dir is None:
            print "Unable to find kitchen meta directory in '%s'" % start_dir
            return False
        recipes_meta_dir = DKKitchenDisk.get_recipes_meta_dir(kitchen_meta_dir)
        if recipes_meta_dir is None:
            print "Unable to find recipes meta directory in '%s'" % start_dir
            return False

        recipe_meta_dir = os.path.join(recipes_meta_dir, self._recipe_name)
        if not os.path.isdir(recipe_meta_dir):
            try:
                os.makedirs(recipe_meta_dir)
            except OSError as e:
                print "%s - %s - %s" % (e.filename, e.errno, e.message)
                return False
        recipes_meta_file = os.path.join(recipe_meta_dir, RECIPE_META)
        try:
            with open(recipes_meta_file, 'w') as f:
                f.write(self._recipe_name)
        except OSError as e:
            print "%s - %s - %s" % (e.filename, e.errno, e.message)
            return False

        orig_head_file = os.path.join(recipe_meta_dir, ORIG_HEAD)
        try:
            with open(orig_head_file, 'w') as f:
                f.write(self._recipe_sha)
        except OSError as e:
            print "%s - %s - %s" % (e.filename, e.errno, e.message)
            return False
        return True

    @staticmethod
    def get_orig_head(start_dir):
        recipe_meta_dir = DKRecipeDisk.find_recipe_meta_dir(start_dir)
        if recipe_meta_dir is None:
            return None

        orig_head = os.path.join(recipe_meta_dir, ORIG_HEAD)
        if not os.path.exists(orig_head):
            return None

        try:
            with open(orig_head, 'r') as f:
                orig_head = f.read()
        except OSError as e:
            print "%s - %s - %s" % (e.filename, e.errno, e.message)
            return None
        return orig_head

    @staticmethod
    def create_conflicts_meta(recipe_meta_dir):
        conflicts_file_path = os.path.join(recipe_meta_dir, DK_CONFLICTS_META)
        if os.path.exists(conflicts_file_path):
            return conflicts_file_path
        else:
            with open(conflicts_file_path, 'w') as conflicts_file:
                conflicts_file.write('{}')
            return conflicts_file_path

    @staticmethod
    def add_conflict_to_conflicts_meta(conflict_info, folder_in_recipe, recipe_name, kitchen_dir):
        recipe_meta_dir = DKKitchenDisk.get_recipe_meta_dir(recipe_name, kitchen_dir)
        conflicts_meta = DKRecipeDisk.get_conflicts_meta(recipe_meta_dir)
        conflict_key = '%s|%s|%s|%s|%s' % (conflict_info['from_kitchen'], conflict_info['to_kitchen'], recipe_name,
                                           folder_in_recipe, conflict_info['filename'])

        conflict_for_save = conflict_info.copy()
        conflict_for_save['folder_in_recipe'] = folder_in_recipe
        conflict_for_save['status'] = 'unresolved'
        if folder_in_recipe not in conflicts_meta:
            conflicts_meta[folder_in_recipe] = {}
        conflicts_meta[folder_in_recipe][conflict_key] = conflict_for_save
        return DKRecipeDisk.save_conflicts_meta(recipe_meta_dir, conflicts_meta)

    @staticmethod
    def get_conflicts_meta(recipe_meta_dir):
        conflicts_file_path = os.path.join(recipe_meta_dir, DK_CONFLICTS_META)
        if not os.path.exists(conflicts_file_path):
            conflicts_file_path = DKRecipeDisk.create_conflicts_meta(recipe_meta_dir)

        with open(conflicts_file_path, 'r') as conflicts_file:
            conflicts = json.load(conflicts_file)
        return conflicts

    @staticmethod
    def get_unresolved_conflicts_meta(recipe_meta_dir, from_kitchen=None, to_kitchen=None):
        conflicts = DKRecipeDisk.get_conflicts_meta(recipe_meta_dir)
        unresolved_conflicts = {}
        for recipe_folder, folder_conflicts in conflicts.iteritems():
            for conflict_key, conflict_info in folder_conflicts.iteritems():
                if conflict_info['status'] == 'unresolved':
                    add_it = True
                    if from_kitchen is not None and to_kitchen is not None:
                        if from_kitchen != conflict_info['from_kitchen'] or conflict_info['to_kitchen'] != to_kitchen:
                            add_it = False
                    if add_it:
                        if recipe_folder not in unresolved_conflicts:
                            unresolved_conflicts[recipe_folder] = {}
                        unresolved_conflicts[recipe_folder][conflict_key] = conflict_info
        return unresolved_conflicts

    @staticmethod
    def get_resolved_conflicts_meta(recipe_meta_dir, from_kitchen=None, to_kitchen=None):
        conflicts = DKRecipeDisk.get_conflicts_meta(recipe_meta_dir)
        resolved_conflicts = {}
        for recipe_folder, folder_conflicts in conflicts.iteritems():
            for conflict_key, conflict_info in folder_conflicts.iteritems():
                if conflict_info['status'] == 'resolved':
                    add_it = True
                    if from_kitchen is not None and to_kitchen is not None:
                        if from_kitchen != conflict_info['from_kitchen'] or conflict_info['to_kitchen'] != to_kitchen:
                            add_it = False
                    if add_it:
                        if recipe_folder not in resolved_conflicts:
                            resolved_conflicts[recipe_folder] = {}
                        resolved_conflicts[recipe_folder][conflict_key] = conflict_info
                    else:
                        print "Found a resolved conflict for from '%s' to '%s', but we are looking for from '%s' to '%s'" % (
                            conflict_info['from_kitchen'], conflict_info['to_kitchen'], from_kitchen, to_kitchen)
        return resolved_conflicts

    @staticmethod
    def resolve_conflict(recipe_meta_dir, recipe_root_dir, file_path):
        all_conflicts = DKRecipeDisk.get_conflicts_meta(recipe_meta_dir)
        norm_file_path = os.path.normpath(file_path)
        local_path_in_recipe = norm_file_path.replace(recipe_root_dir, '')
        local_path_in_recipe = re.sub("^" + os.sep + "|/$", "", local_path_in_recipe)
        recipe_name = DKRecipeDisk.find_recipe_name(recipe_root_dir)
        for recipe_folder, folder_contents in all_conflicts.iteritems():
            for conflict_key, conflict_info in folder_contents.iteritems():
                if conflict_info['status'] == 'unresolved':
                    path_in_recipe = os.path.join(conflict_info['folder_in_recipe'], conflict_info['filename'])
                    path_in_recipe = re.sub(r'%s/' % recipe_name, r'', path_in_recipe)
                    if local_path_in_recipe == path_in_recipe:
                        conflict_info['status'] = 'resolved'
                        folder_contents[conflict_key] = conflict_info
                        DKRecipeDisk.save_conflicts_meta(recipe_meta_dir, all_conflicts)
                        return True
        return False

    @staticmethod
    def save_conflicts_meta(recipe_meta_dir, conflicts_meta):
        conflicts_file_path = os.path.join(recipe_meta_dir, DK_CONFLICTS_META)
        with open(conflicts_file_path, 'w') as conflicts_file:
            conflicts_file.write(json.dumps(conflicts_meta, sort_keys=True, indent=2, separators=(',', ': ')))
        return True

    @staticmethod
    def _get_my_recipe_meta(kitchen_meta_dir, recipe_name):
        recipe_meta_file_path = os.path.join(DKKitchenDisk.get_recipes_meta_dir(kitchen_meta_dir), recipe_name,
                                             RECIPE_META)
        if not os.path.isfile(recipe_meta_file_path):
            return None

        with open(recipe_meta_file_path, 'r') as recipe_meta_file:
            contents = recipe_meta_file.read()
        return contents

    @staticmethod
    def find_recipe_root_dir(check_dir=None):
        return DKRecipeDisk._find_recipe(check_dir, return_recipe_root_path=True)

    @staticmethod
    def find_recipe_meta_dir(check_dir=None):
        recipe_root_dir = DKRecipeDisk.find_recipe_root_dir(check_dir)
        if recipe_root_dir is None:
            return None

        recipe_name = DKRecipeDisk.find_recipe_name(recipe_root_dir)
        if recipe_name is None:
            return None

        kitchen_meta_dir = DKKitchenDisk.find_kitchen_meta_dir(recipe_root_dir)
        if kitchen_meta_dir is None:
            print "Unable to find kitchen meta directory in '%s'" % check_dir
            return False

        recipes_meta_dir = DKKitchenDisk.get_recipes_meta_dir(kitchen_meta_dir)
        if recipes_meta_dir is None:
            print "Unable to find recipes meta directory in '%s'" % check_dir
            return False

        recipe_meta_dir = os.path.join(recipes_meta_dir, recipe_name)
        return recipe_meta_dir

    @staticmethod
    def is_recipe_root_dir(check_dir=None):
        found_path = DKRecipeDisk._find_recipe(check_dir, return_recipe_root_path=True)
        if found_path == check_dir:
            return True
        else:
            return False

    @staticmethod
    def find_recipe_name(walk_dir=None):
        return DKRecipeDisk._find_recipe(walk_dir)

    @staticmethod
    def _find_recipe(walk_dir=None, return_recipe_root_path=False):

        if walk_dir is None:
            walk_dir = os.getcwd()

        kitchen_meta_dir = DKKitchenDisk.find_kitchen_meta_dir(walk_dir)
        if kitchen_meta_dir is None:
            # We aren't in a kitchen folder.
            return None

        kitchen_root_dir = DKKitchenDisk.find_kitchen_root_dir(walk_dir)
        if kitchen_root_dir is None:
            # We aren't in a kitchen folder.
            return None

        if walk_dir == kitchen_root_dir or walk_dir == kitchen_meta_dir:
            # We are in the kitchen root folder. Can't do anything here.
            return None

        current_dir_abs = os.path.abspath(walk_dir)
        kitchen_root_dir_abs = os.path.abspath(kitchen_root_dir)

        common = os.path.commonprefix([current_dir_abs, kitchen_root_dir_abs])
        current_dir_relative = current_dir_abs.replace(common + os.sep, '')
        parts = current_dir_relative.split(os.sep)
        if len(parts) == 0:
            # Looks like we are in the kitchen folder.
            return None

        recipe_name = parts[0]
        recipe_meta_contents = DKRecipeDisk._get_my_recipe_meta(kitchen_meta_dir, recipe_name)
        if recipe_name == recipe_meta_contents:
            if not return_recipe_root_path:
                return recipe_name
            else:
                return os.path.join(kitchen_root_dir, recipe_name)
        else:
            return None

    @staticmethod
    def sort_file(list_of_files):

        # sorted_files = dict()
        # for this_file in list_of_files:
        #    file_name = this_file
        return list_of_files

    @staticmethod
    def write_files(full_dir, file_dict):
        if 'filename' in file_dict:
            abspath = os.path.join(full_dir, file_dict['filename'])
            with open(abspath, 'wb') as the_file:
                the_file.seek(0)
                the_file.truncate()
                if 'json' in file_dict:
                    if isinstance(file_dict['json'], dict) is True:
                        json.dump(file_dict['json'], the_file, indent=4)
                    else:
                        the_file.write(file_dict['json'])
                elif 'text' in file_dict:
                    the_file.seek(0)
                    the_file.truncate()
                    the_file.write(file_dict['text'])


# http://stackoverflow.com/questions/4187564/recursive-dircmp-compare-two-directories-to-ensure-they-have-the-same-files-and
class dircmp(filecmp.dircmp):
    """
    Compare the content of dir1 and dir2. In contrast with filecmp.dircmp, this
    subclass compares the content of files with the same path.
    """

    def phase3(self):
        """
        Find out differences between common files.
        Ensure we are using content comparison with shallow=False.
        """
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files,
                                 shallow=False)
        self.same_files, self.diff_files, self.funny_files = fcomp


def is_same(dir1, dir2):
    """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    :param dir2:
    :param dir1:
    """
    compared = dircmp(dir1, dir2, IGNORED_FILES)  # ignore the OS X file
    if compared.left_only or compared.right_only or compared.diff_files or compared.funny_files:
        return False
    for subdir in compared.common_dirs:
        if not is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)):
            return False
    return True



def flatten_tree(remote_sha):
    flattened_tree = {}
    return flattened_tree


def compare_sha(remote_sha, local_sha):
    same = dict()
    different = dict()
    only_local = dict()
    only_remote = dict()
    # Look for differences from remote
    for remote_path in remote_sha:
        if remote_path in local_sha:
            for remote_file in remote_sha[remote_path]:
                local_files_found = filter(lambda local_file: local_file['filename'] == remote_file['filename'],
                                           local_sha[remote_path])
                if len(local_files_found) != 0:
                    if local_files_found[0]['sha'] == remote_file['sha']:
                        # print '%s matches' % remote_file['filename']
                        if remote_path not in same:
                            same[remote_path] = list()
                        same[remote_path].append(remote_file)
                    else:
                        if remote_path not in different:
                            different[remote_path] = list()
                        # print '%s different' % remote_file['filename']
                        different[remote_path].append(remote_file)
                elif len(local_files_found) > 1:
                    # print 'compare_sha: Unexpected return in remote_path'
                    raise
                else:
                    # print '%s not found for local' % remote_file['filename']
                    if remote_path not in only_remote:
                        only_remote[remote_path] = list()
                    only_remote[remote_path].append(remote_file)
        else:
            # print '%s missing from local' % remote_path
            if remote_path not in only_remote:
                only_remote[remote_path] = list()

    ignore = DKIgnore()
    for local_path, local_files in local_sha.iteritems():
        if ignore.ignore(local_path):
            # Ignore some stuff.
            # print '%s ignoring' % local_path
            continue
        elif local_path in remote_sha:
            for local_file in local_files:
                if ignore.ignore(local_file['filename']):
                    # print '%s ignoring' % local_file['filename']
                    continue
                elif ignore.ignore(os.path.join(local_path, local_file['filename'])):
                    # print '%s ignoring' % os.path.join(local_path, local_file['filename'])
                    continue
                remote_files_found = filter(lambda remote_file: remote_file['filename'] == local_file['filename'],
                                            remote_sha[local_path])
                if len(remote_files_found) > 1:
                    # print 'compare_sha: Unexpected return in remote_path'
                    raise
                elif len(remote_files_found) == 0:
                    if local_path not in only_local:
                        only_local[local_path] = list()
                    # print '%s missing from remote' % local_file['filename']
                    only_local[local_path].append(local_file)
        else:
            if local_path not in only_local:
                # print '%s missing from remote' % local_path
                only_local[local_path] = list()

    rv = dict()
    rv['same'] = same
    rv['different'] = different
    rv['only_local'] = only_local
    rv['only_remote'] = only_remote
    return rv


def get_directory_sha(walk_dir):
    recipe_name = os.path.basename(walk_dir)
    rootdir = os.path.dirname(walk_dir)
    r = dict()
    r[recipe_name] = []
    for root, subdirs, files in os.walk(walk_dir):
        for filename in files:
            if not filename in IGNORED_FILES:
                file_path = os.path.join(root, filename)
                part = file_path.split(rootdir, 1)[1]
                part2 = part.split(filename, 1)[0]
                part3 = part2[1:-1]
                with open(file_path) as file_obj:
                    r[part3].append({'filename': filename, 'sha': githash_fileobj(file_obj)})
        for subdir in subdirs:
            subdir_fullpath = os.path.join(root, subdir)
            part = subdir_fullpath.split(rootdir, 1)[1]
            part2 = part[1:]
            r[part2] = []
    return r
