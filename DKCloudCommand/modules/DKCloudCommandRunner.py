import os
import json
import base64
import zlib
from .DKCloudAPI import DKCloudAPI
from .DKRecipeDisk import DKRecipeDisk
from .DKKitchenDisk import DKKitchenDisk
from .DKReturnCode import *
from .DKIgnore import DKIgnore
from .DKActiveServingWatcher import DKActiveServingWatcherSingleton
from .DKActiveServingWatcher import DKActiveServingWatcher
import jwt
import sys
import pprint
from prettytable import PrettyTable, PLAIN_COLUMNS, MSWORD_FRIENDLY

__author__ = 'DataKitchen, Inc.'


def check_api_param_decorator(func):
    def check_api_wrapper(*args, **kwargs):
        if not isinstance(args[0], DKCloudAPI):
            if 'modules.DKCloudAPI.DKCloudAPI' in str(type(args[0])):
                return func(*args, **kwargs)
            else:
                return 'ERROR: DKCloudCommandRunner bad parameters \n'
        else:
            return func(*args, **kwargs)

    return check_api_wrapper


# The goal of this file is to take the output from the CLI commands and
#  pretty print them for the user (human)
# Eventually make different types of output formats
#  ould add JSON (json), tab-delimited (text), ascii-formatted table (table)


class DKCloudCommandRunner(object):
    def __init__(self):
        pass

    TESTRESULTS = 'testresults'
    TIMINGRESULTS = 'timingresults'
    STATUSES = 'statuses'
    SERVING = 'serving'
    LOGS = 'log'
    RECIPENAME = 'recipe'
    SERVINGID = 'serving-id'
    KITCHEN = 'kitchenname'
    STATE = 'state'
    SUMMARY = 'summary'
    TIMESTAMP = 'start-time'

    ORDER_ID = 'serving_chronos_id'
    ORDER_RUN_ID = 'serving_mesos_id'

    @staticmethod
    @check_api_param_decorator
    def rude(dk_api):
        rude = dk_api.rude()
        if rude is None:
            rs = 'ERROR:  DKCloudCommand.rude failed'
        else:
            rs = "DKCloudCommand.rude = %s\n" % rude
        return rs

    @staticmethod
    @check_api_param_decorator
    def list_kitchen(dk_api):
        rc = dk_api.list_kitchen()
        if rc.ok():
            kl = rc.get_payload()
            if kl is not None and len(kl) > 0:
                rs = 'kitchen-list returned %d kitchens\n' % len(kl)
                sorted_list = sorted(kl, key=lambda j: j['name'].lower())  # sort the list, ignore case
                for k in sorted_list:
                    rs += '  %s\t--parent--> %s\n' % (k['name'], k['parent-kitchen'])
                rc.set_message(rs)
            else:
                rc.set_message('No kitchens found.')
        else:
            rc.set_message('unable to list kitchens\nmessage: %s' % rc.get_message())
        return rc


    @staticmethod
    @check_api_param_decorator
    def secret_list(dk_api,path):
        rc = dk_api.secret_list(path)
        if rc.ok():
            sl = rc.get_payload()
            if sl:
                rs = 'secret-list returned %d secrets\n' % len(sl)
                sorted_list = sorted(sl)
                for s in sorted_list:
                    rs += '\t%s\n' % s
                rc.set_message(rs)
            else:
                rc.set_message('No secrets found.')
        else:
            rc.set_message('Unable to list secrets\nmessage: %s' % rc.get_message())
        return rc

    @staticmethod
    @check_api_param_decorator
    def secret_exists(dk_api,path):
        rc = dk_api.secret_exists(path)
        if rc.ok():
            sl = rc.get_payload()
            rc.set_message(sl)
        else:
            rc.set_message('Unable to check if secret exists\nmessage: %s' % rc.get_message())
        return rc

    @staticmethod
    @check_api_param_decorator
    def secret_write(dk_api,path,value):
        rc = dk_api.secret_write(path,value)
        if rc.ok():
            rc.set_message('Secret written.')
        else:
            rc.set_message('Unable write secret\nmessage: %s' % rc.get_message())
        return rc

    @staticmethod
    @check_api_param_decorator
    def secret_delete(dk_api,path):
        rc = dk_api.secret_delete(path)
        if rc.ok():
            rc.set_message('Secret deleted.')
        else:
            rc.set_message('Unable deleted secret\nmessage: %s' % rc.get_message())
        return rc

    @staticmethod
    @check_api_param_decorator
    def user_info(dk_api):
        rc = DKReturnCode()
        encoded_token = dk_api.login()
        try:
            jwt_payload = jwt.decode(
                jwt=encoded_token,
                verify=False
            )
            rc.set(rc.DK_SUCCESS, pprint.pprint(jwt_payload))
        except jwt.ExpiredSignature:
            rc.set(rc.DK_FAIL, 'token is expired')
        except jwt.DecodeError:
            rc.set(rc.DK_FAIL, 'token signature is invalid')
        except jwt.InvalidIssuedAtError as jwt_e:
            rc.set(rc.DK_FAIL, jwt_e.message)
        except:
            rc.set(rc.DK_FAIL, '%s' % sys.exc_info()[0])
        return rc

    @staticmethod
    @check_api_param_decorator
    def get_kitchen(dk_api, kitchen_name, root_dir, recipes=None, get_all_recipes=False):
        rc = DKReturnCode()
        msg_with_status = ''
        if kitchen_name is None or len(kitchen_name) == 0:
            rc.set(rc.DK_FAIL, 'DKCloudCommandRunner bad parameters - kitchen')
            return rc

        if not DKKitchenDisk.check_kitchen_folder(kitchen_name, root_dir):
            rc.set(rc.DK_FAIL, "Cannot get Kitchen '%s' to folder '%s'" % (kitchen_name, root_dir))
            return rc

        lkrc = dk_api.list_kitchen()
        kl = lkrc.get_payload()
        found_kitchens = [found_kitchen for found_kitchen in kl if found_kitchen['name'] == kitchen_name]
        if len(found_kitchens) > 1:
            rc.set(rc.DK_FAIL, "ERROR: Found multiple kitchens named '%s'" % kitchen_name)
            return rc
        elif len(found_kitchens) == 0:
            rc.set(rc.DK_FAIL, "ERROR: Kitchen '%s' not found on server" % kitchen_name)
            return rc
        elif len(found_kitchens) == 1:
            if DKKitchenDisk.write_kitchen(kitchen_name, root_dir):
                msg_with_status = "Got Kitchen '%s'" % kitchen_name
            else:
                rc.set(rc.DK_FAIL, "Problems getting '%s' kitchen" % kitchen_name)
                return rc

        if get_all_recipes:
            recipe_list = dk_api.list_recipe(kitchen_name)
            if recipe_list is None:
                rc.set(rc.DK_FAIL, 'ERROR:  DKCloudCommand.list_recipe failed')
                return rc
            else:
                recipes_to_get = recipe_list
        elif recipes is not None and len(recipes) > 0:
            recipes_to_get = recipes
        else:
            recipes_to_get = None

        if recipes_to_get is not None:
            for recipe in recipes_to_get:
                rc = DKCloudCommandRunner.get_recipe(dk_api, kitchen_name, recipe, os.path.join(root_dir, kitchen_name))
                rv = rc.get_message()
                if not rc.ok():
                    rc.set(rc.DK_FAIL, rv)
                    return rc
                else:
                    msg_with_status += "\n" + rv
        rc.set(rc.DK_SUCCESS, msg_with_status)
        return rc

    @staticmethod
    def _list_kitchen_variables(kitchen_overrides):
        msg = ''
        if len(kitchen_overrides) > 0:
            field_names = ['Variable Name', 'Value']
            x = PrettyTable()
            x.field_names = field_names
            x.set_style(PLAIN_COLUMNS)
            x.header = True
            x.border = False
            x.align["Variable Name"] = "l"
            x.align["Value"] = "l"
            x.left_padding_width = 1
            row = ['----------------', '----------------']
            x.add_row(row)
            for override in kitchen_overrides:
                row = [override['variable'], override['value']]
                x.add_row(row)
            msg += '\nRecipe Overrides\n'
            msg += x.get_string() + '\n'
        else:
            msg += 'No recipe overrides for this kitchen'
        return msg

    @staticmethod
    def config_kitchen(dk_api, kitchen, add=(), get=(), unset=(), listall=False):
        rc = DKReturnCode()

        if len(add) == 0 and len(get) ==0 and len(unset) ==0 and listall == False:
            rc.set(rc.DK_SUCCESS, 'Nothing to do')
            return rc

        output_message = ''
        if len(add) != 0 or len(unset) != 0:
            rv = dk_api.modify_kitchen_settings(kitchen, add=add, unset=unset)
            if rv.ok():
                overrides = rv.get_payload()
                modified_message = rv.get_message()
                output_message += modified_message
            else:
                list_msg = 'Unable to update recipe overrides.\n'
                rc.set(rc.DK_FAIL, list_msg)
                return rc
        else:
            overrides = None

        if listall:
            if overrides is None:
                rv = dk_api.get_kitchen_settings(kitchen)
                if rv.ok():
                    kitchen_json = rv.get_payload()
                    overrides = kitchen_json['recipeoverrides']
                    list_msg = DKCloudCommandRunner._list_kitchen_variables(overrides)
                    output_message += list_msg
                else:
                    list_msg = 'Unable to get recipe overrides.\n'
                    rc.set(rc.DK_FAIL, list_msg)
                    return rc
            elif overrides is not None:
                list_msg = DKCloudCommandRunner._list_kitchen_variables(overrides)
                output_message += list_msg
            rc.set(rc.DK_SUCCESS, output_message, overrides)
            return rc

        if len(get) != 0:
            rv = dk_api.get_kitchen_settings(kitchen)
            if rv.ok():
                kitchen_json = rv.get_payload()
                overrides = kitchen_json['recipeoverrides']
                if isinstance(get, tuple) or isinstance(get, list):
                    for get_this in get:
                        matches = [override for override in overrides if override['variable'] == get_this]
                        if len(matches) == 0:
                            output_message += "none\n"
                        else:
                            output_message += "{}\n".format(matches[0]['value'])
                else:
                    matches = [override for override in overrides if override['variable'] == get]
                    if len(matches) == 0:
                        output_message += "none\n"
                    else:
                        output_message += "{}\n".format(matches[0]['value'])
            else:
                msg = 'Unable to get {}\n'.format(get)
                rc.set(rc.DK_FAIL, msg)
                return rc
        rc.set(rc.DK_SUCCESS, output_message, overrides)
        return rc

    @staticmethod
    def which_kitchen(dk_api, path=None):
        kitchen_name = DKKitchenDisk.find_kitchen_name(path)
        rc = DKReturnCode()
        if kitchen_name is None:
            rs = 'DKCloudCommand.which_kitchen unable to determine kitchen\nmessage: %s' % rc.get_message()
            rc.set(rc.DK_FAIL, rs)
            return rc
        else:
            rs = "You are in kitchen '%s'" % kitchen_name
        rc.set(rc.DK_SUCCESS, rs)
        return rc

    @staticmethod
    def which_kitchen_name(path=None):
        return DKKitchenDisk.find_kitchen_name(path)

    @staticmethod
    @check_api_param_decorator
    def create_kitchen(dk_api, parent_kitchen, new_kitchen):
        kl = dk_api.create_kitchen(parent_kitchen, new_kitchen, 'junk')
        if kl.ok():
            kl.set_message('DKCloudCommand.create_kitchen created %s\n' % new_kitchen)
        else:
            kl.set_message('ERROR:  DKCloudCommand.create_kitchen failed\nmessage: %s' %
                           kl.get_message())
        return kl

    @staticmethod
    @check_api_param_decorator
    def delete_kitchen(dk_api, kitchen):
        odrc = dk_api.order_delete_all(kitchen)
        msg = odrc.get_message()
        kl = dk_api.delete_kitchen(kitchen, 'delete kitchen')
        if kl.ok():
            kl.set_message('>%s<\ndeleted kitchen %s\n' % (msg, kitchen))
        else:
            kl.set_message('>%s<\nunable to delete %s\nmessage: %s' % (msg, kitchen, kl.get_message()))
        return kl

    @staticmethod
    @check_api_param_decorator
    def list_recipe(dk_api, kitchen):
        rc = dk_api.list_recipe(kitchen)
        if not rc.ok():
            s = 'DKCloudCommand.list_recipe failed\nmessage: %s' % rc.get_message()
        else:
            rl = rc.get_payload()
            s = 'DKCloudCommand.list_recipe returned %d recipes\n' % len(rl)
            for r in rl:
                s += '  %s\n' % r
        rc.set_message(s)
        return rc

    @staticmethod
    @check_api_param_decorator
    def recipe_create(dk_api, kitchen, name):
        rc = dk_api.recipe_create(kitchen, name)
        if not rc.ok():
            s = 'DKCloudCommand.recipe_create failed\nmessage: %s' % rc.get_message()
        else:
            rl = rc.get_payload()
            s = 'DKCloudCommand.recipe_create created recipe %s\n' % name
        rc.set_message(s)
        return rc

    @staticmethod
    @check_api_param_decorator
    def get_recipe(dk_api, kitchen, recipe_name_param, start_dir=None):
        rc = DKReturnCode()
        if start_dir is None:
            rp = os.getcwd()
        else:
            if os.path.isdir(start_dir) is False:
                s = 'ERROR: DKCloudCommandRunner path (%s) does not exist' % start_dir
                rc.set(rc.DK_FAIL, s)
                return rc
            rp = start_dir

        if not DKKitchenDisk.is_kitchen_root_dir(rp):
            recipe_name_found = DKRecipeDisk.find_recipe_name(rp)
            if recipe_name_found != recipe_name_param:
                s = "ERROR: DKCloudCommandRunner.get_recipe: You are asking to get recipe '%s', but you are in folder '%s'" % (
                recipe_name_param, rp)
                rc.set(rc.DK_FAIL, s)
                return rc
            rp = DKKitchenDisk.find_kitchen_root_dir(rp)

        if os.path.exists(os.path.join(rp, recipe_name_param)):
            # The recipe folder already exists. Compare the files, and see if there will be any conflicts.
            recipe_path = os.path.join(rp, recipe_name_param)
            rc = dk_api.recipe_status(kitchen, recipe_name_param, recipe_path)
            if not rc.ok():
                rs = 'DKCloudCommand.recipe_status failed\nmessage: %s' % rc.get_message()
                rc.set_message(rs)
                return rc

            rl = rc.get_payload()

            if 'different' in rl and len(rl['different']) > 0:
                status, merged_different_files = DKCloudCommandRunner._merge_files(dk_api, kitchen, recipe_name_param,
                                                                                   recipe_path, rl['different'])
                if not status:
                    diffs_no_recipe = list()
                    for diff in rl['different']:
                        diffs_no_recipe.append(diff.split(recipe_name_param + os.sep)[1])
                    s = """ERROR: DKCloudCommandRunner.get_recipe: There was trouble merging the differences between local and remote files.
                        %s
                        Use file-diff and file-merge to resolve issues.
                        No files written locally.""" % "\n".join(diffs_no_recipe)
                    rc.set(rc.DK_FAIL, s)
                    return rc
            else:
                merged_different_files = None

            if 'only_remote' in rl and len(rl['only_remote']) > 0:
                folders_stripped = list()
                files_stripped = list()
                for remote_path, remote_files in rl['only_remote'].items():
                    parts = remote_path.partition(os.sep)
                    if len(remote_files) == 0:
                        folders_stripped.append(parts[2])
                    else:
                        for remote_file in remote_files:
                            files_stripped.append(os.path.join(parts[2], remote_file['filename']))

                minimal_paths = DKCloudCommandRunner.find_minimal_paths_to_get(folders_stripped)
                paths_to_get = []
                for path, is_path in minimal_paths.items():
                    paths_to_get.append(os.path.join(path, '*'))
                paths_to_get.extend(files_stripped)
                only_remote_files_rc = dk_api.get_recipe(kitchen, recipe_name_param, paths_to_get)

                if only_remote_files_rc is not None:
                    remote_only_recipe_tree = only_remote_files_rc.get_payload()
                else:
                    remote_only_recipe_tree = None

            else:
                remote_only_recipe_tree = None

            # Start building the return message
            msg = ''

            # We are trying to get the local up to date with the remote.
            # Different diff results are different actions:
            # local_only - Do nothing
            # same - Do nothing
            # remote_only - Write new
            # different (merged_different_files) - overwrite
            remote_only_msg = ''
            if remote_only_recipe_tree is not None:
                r = DKRecipeDisk(recipe=remote_only_recipe_tree['recipes'][recipe_name_param], path=rp)
                if not r.save_recipe_to_disk(update_meta=False):
                    rc.set(rc.DK_FAIL, 'Problems saving differences and remote only files to disk. %s' % str(
                        remote_only_recipe_tree))
                    return rc

                remote_only_file_count = 0
                remote_only_files = list()
                for recipe_folder_name, recipe_folder_contents in remote_only_recipe_tree['recipes'][
                        recipe_name_param].items():
                    for remote_only_file in recipe_folder_contents:
                        remote_only_file_count += 1
                        remote_only_files.append(
                            "\t%s" % os.path.join(os.sep.join(recipe_folder_name.split(os.sep)[1:]),
                                                  remote_only_file['filename']))
                remote_only_msg += '%d new or missing files from remote:\n' % remote_only_file_count
                remote_only_files.sort()
                remote_only_msg += '\n'.join(remote_only_files)

            merged_files_msg = ''

            if merged_different_files is not None:
                r = DKRecipeDisk(recipe=merged_different_files, path=rp)
                if not r.save_recipe_to_disk(update_meta=False):
                    rc.set(rc.DK_FAIL, 'Problems saving differences and remote only files to disk. %s' % str(
                        merged_different_files))
                    return rc

                merged_file_count = 0
                conflicted_file_count = 0
                for merged_folder, folder_contents in merged_different_files.items():
                    for merged_file in folder_contents:
                        # conflict_key = '%s|%s|%s|%s|%s' % (
                        # conflict_info['from_kitchen'], conflict_info['to_kitchen'], recipe_name,
                        # folder_in_recipe, conflict_info['filename'])
                        #
                        # conflict_for_save = conflict_info.copy()
                        # conflict_for_save['folder_in_recipe'] = folder_in_recipe
                        # conflict_for_save['status'] = 'unresolved'
                        conflict_info = dict()
                        if 'text' in merged_file:
                            conflict_info['conflict_tags'] = merged_file['text']
                        elif 'json' in merged_file:
                            conflict_info['conflict_tags'] = merged_file['json']
                        elif 'content' in merged_file:
                            conflict_info['conflict_tags'] = merged_file['content']

                        merged_file_path = os.path.join(os.sep.join(merged_folder.split(os.sep)[1:]), merged_file['filename'])
                        merged_files_msg += "Auto-merging '%s'\n" % merged_file_path
                        merged_file_count += 1
                        if '<<<<<<<' in conflict_info['conflict_tags'] and '=======' in conflict_info['conflict_tags'] \
                                and '>>>>>>>' in conflict_info['conflict_tags']:
                            conflicted_file_count += 1
                            conflict_info['filename'] = os.path.basename(merged_file['filename'])
                            conflict_info['from_kitchen'] = kitchen
                            conflict_info['sha'] = 'none'
                            conflict_info['to_kitchen'] = kitchen
                            DKRecipeDisk.add_conflict_to_conflicts_meta(conflict_info, merged_folder, recipe_name_param,
                                                                        rp)
                            merged_files_msg += "CONFLICT (content): Merge conflict in %s\n" % merged_file_path

            if len(remote_only_msg) > 0:
                msg += remote_only_msg + '\n'
            if len(merged_files_msg) > 0:
                msg += merged_files_msg + '\n'

            if len(msg) == 0:
                msg = 'Nothing to do'
            rc.set(DKReturnCode.DK_SUCCESS, msg)
            return rc
        else:
            rc = DKCloudCommandRunner._get_recipe_new(dk_api, kitchen, recipe_name_param, rp)
        return rc

    @staticmethod
    def find_minimal_paths_to_get(paths_to_check):
        minimum_paths = {}
        skip_paths = {}
        paths_to_check.sort()
        for outer in range(0, len(paths_to_check)):
            this_path = paths_to_check[outer]
            if this_path not in skip_paths:
                if outer == len(paths_to_check) - 1 and this_path not in skip_paths and this_path not in minimum_paths:
                    minimum_paths[this_path] = False
                    continue
                for inner in range(outer + 1, len(paths_to_check)):
                    next_path = paths_to_check[inner]
                    if next_path not in skip_paths:
                        if DKCloudCommandRunner.is_subdirectory(next_path, this_path):
                            minimum_paths[this_path] = True
                            skip_paths[next_path] = True
            if this_path not in skip_paths and this_path not in minimum_paths:
                minimum_paths[this_path] = False
        return minimum_paths

    @staticmethod
    def os_path_split_asunder(path, debug=False):
        """
        http://stackoverflow.com/a/4580931/171094
        """
        parts = []
        while True:
            newpath, tail = os.path.split(path)
            if debug: print(repr(path), (newpath, tail))
            if newpath == path:
                assert not tail
                if path: parts.append(path)
                break
            parts.append(tail)
            path = newpath
        parts.reverse()
        return parts

    # From http://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory/17624617#17624617
    @staticmethod
    def is_subdirectory(potential_subdirectory, expected_parent_directory):
        """
        Is the first argument a sub-directory of the second argument?

        :param potential_subdirectory:
        :param expected_parent_directory:
        :return: True if the potential_subdirectory is a child of the expected parent directory

        """

        def _get_normalized_parts(path):
            return DKCloudCommandRunner.os_path_split_asunder(os.path.realpath(os.path.abspath(os.path.normpath(path))))

        # make absolute and handle symbolic links, split into components
        sub_parts = _get_normalized_parts(potential_subdirectory)
        parent_parts = _get_normalized_parts(expected_parent_directory)

        if len(parent_parts) > len(sub_parts):
            # a parent directory never has more path segments than its child
            return False

        # we expect the zip to end with the short path, which we know to be the parent
        return all(part1 == part2 for part1, part2 in zip(sub_parts, parent_parts))

    @staticmethod
    def _merge_files(dk_api, kitchen_name, recipe_name, recipe_path, differences):
        merged_files = dict()
        status = True
        for folder_name, folder_contents in differences.items():
            for this_file in folder_contents:

                rc = DKCloudCommandRunner._merge_file(dk_api, kitchen_name, recipe_name, recipe_path, folder_name,
                                                      this_file)
                if rc.ok():
                    payload = rc.get_payload()
                    if payload['status'] == 'success':
                        if folder_name not in merged_files:
                            merged_files[folder_name] = list()
                        this_file['text'] = base64.b64decode(payload['merged_content'])
                        merged_files[folder_name].append(this_file)
                    else:
                        status = False
                else:
                    status = False
        return status, merged_files

    @staticmethod
    def _merge_file(dk_api, kitchen_name, recipe_name, recipe_path, folder_name, file_info):
        # /v2/file/merge/<string:kitchenname>/<string:recipename>/<path:filepath>
        kitchen_root_dir = DKKitchenDisk.find_kitchen_root_dir(recipe_path)
        orig_head = DKRecipeDisk.get_orig_head(recipe_path)
        if orig_head is None:
            return None
        last_file_sha = 'none'
        try:
            with open(os.path.join(kitchen_root_dir, folder_name, file_info['filename']), 'r') as f:
                local_contents = f.read()
        except OSError as e:
            print("%s - %s - %s" % (e.filename, e.errno, e.message))
            return None

        file_path_without_recipe = os.path.join(os.sep.join(folder_name.split(os.sep)[1:]), file_info['filename'])
        rc = dk_api.merge_file(kitchen_name, recipe_name, file_path_without_recipe, base64.b64encode(local_contents),
                               orig_head, last_file_sha)
        return rc

    @staticmethod
    def _get_recipe_new(dk_api, kitchen, recipe_name_param, rp):
        rc = dk_api.get_recipe(kitchen, recipe_name_param)
        recipe_info = rc.get_payload()
        if isinstance(recipe_info, dict) and 'recipes' in recipe_info:
            recipes = recipe_info['recipes']
            if not rc.ok():
                s = 'ERROR:  DKCloudCommand.get_recipe failed'
                rc.set_message('%s\nmessage: %s' % (s, rc.get_message()))
            else:
                rs = 'DKCloudCommand.get_recipe has %d sections\n' % len(recipes[recipe_name_param])
                for r in recipes[recipe_name_param]:
                    rs += '  %s\n' % r
                rc.set_message(rs)
                d = DKRecipeDisk(recipe_info['ORIG_HEAD'], recipes[recipe_name_param], rp)
                rv = d.save_recipe_to_disk()
                if rv is None:
                    s = 'ERROR: could not save recipe to disk'
                    rc.set(rc.DK_FAIL, s)
        else:
            if len(rc.get_message()) > 0:
                rc.set(rc.DK_FAIL, rc.get_message())
            else:
                rc.set(rc.DK_FAIL, rc.get_payload())
        return rc

    @staticmethod
    @check_api_param_decorator
    def recipe_status(dk_api, kitchen, recipe, recipe_path_param=None):
        if recipe_path_param is None:
            recipe_path_to_use = os.getcwd()
        else:
            if os.path.isdir(recipe_path_param) is False:
                return 'ERROR: DKCloudCommandRunner path (%s) does not exist' % recipe_path_param
            recipe_path_to_use = recipe_path_param
        rc = dk_api.recipe_status(kitchen, recipe, recipe_path_to_use)
        if not rc.ok():
            rc.set_message('DKCloudCommand.recipe_status failed\nmessage: %s' % rc.get_message())
            return rc
        else:
            rl = rc.get_payload()
            same_file_count = 0
            if len(rl['same']) > 0:
                for folder_name, folder_contents in rl['same'].items():
                    same_file_count += len(folder_contents)

            modified_file_names = list()
            modified_file_count = 0
            if len(rl['different']) > 0:
                for folder_name, folder_contents in rl['different'].items():
                    for this_file in folder_contents:
                        modified_file_names.append(
                            '\t' + os.path.join(os.sep.join(folder_name.split(os.sep)[1:]), this_file['filename']))
                        modified_file_count += 1

            local_file_names = list()
            local_file_count = 0
            local_folder_names = list()
            local_folder_count = 0
            if len(rl['only_local']) > 0:
                for folder_name, folder_contents in rl['only_local'].items():
                    if len(folder_contents) > 0:
                        for this_file in folder_contents:
                            local_file_names.append(
                                '\t' + os.path.join(os.sep.join(folder_name.split(os.sep)[1:]), this_file['filename']))
                            local_file_count += 1
                    else:
                        local_folder_count += 1
                        local_folder_names.append(
                            '\t' + os.sep.join(folder_name.split(os.sep)[1:]))

            remote_file_names = list()
            remote_file_count = 0
            remote_folder_count = 0
            remote_folder_names = list()
            if len(rl['only_remote']) > 0:
                for folder_name, folder_contents in rl['only_remote'].items():
                    if len(folder_contents) > 0:
                        for this_file in folder_contents:
                            remote_file_names.append(
                                '\t' + os.path.join(os.sep.join(folder_name.split(os.sep)[1:]), this_file['filename']))
                            remote_file_count += 1
                    else:
                        remote_folder_count += 1
                        remote_folder_names.append(
                            '\t' + os.sep.join(folder_name.split(os.sep)[1:]))
            msg = ''
            if modified_file_count > 0:
                modified_file_names.sort()
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d files are modified:' % modified_file_count + '\n' + '\n'.join(modified_file_names) + '\n'
            if local_file_count > 0:
                local_file_names.sort()
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d files are local only:' % local_file_count + '\n' + '\n'.join(local_file_names) + '\n'
            if local_folder_count > 0:
                local_folder_names.sort()
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d directories are local only:' % local_folder_count + '\n' + '\n'.join(local_folder_names) + '\n'
            if remote_file_count > 0:
                remote_file_names.sort()
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d files are remote only:' % remote_file_count + '\n' + '\n'.join(remote_file_names) + '\n'
            if remote_folder_count > 0:
                remote_folder_names.sort()
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d directories are remote only:' % remote_folder_count + '\n' + '\n'.join(remote_folder_names) + '\n'
            if same_file_count > 0:
                if len(msg) > 0:
                    msg += '\n'
                msg += '%d files are unchanged' % same_file_count + '\n'
            rc.set_message(msg)
            return rc

    @staticmethod
    @check_api_param_decorator
    def update_all_files(dk_api, kitchen, recipe_name, recipe_dir, message, dryrun=False):
        """
        reutrns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string  -- kitchen name, string
        :param recipe_dir: string - path to the root of the directory
        :param message: string message -- commit message, string
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if kitchen is None or recipe_name is None or message is None:
            s = 'ERROR: DKCloudCommandRunner bad input parameters'
            rc.set(rc.DK_FAIL, s)
            return rc

        rc = dk_api.recipe_status(kitchen, recipe_name, recipe_dir)
        if not rc.ok():
            rs = 'DKCloudCommand.update_all_files failed\nmessage: %s' % rc.get_message()
            rc.set_message(rs)
            return rc

        rl = rc.get_payload()
        if (len(rl['different']) + len(rl['only_local']) + len(rl['only_remote'])) == 0:
            rs = 'DKCloudCommand.update_all_files no files changed.'
            rc.set_message(rs)
            return rc

        rc = DKCloudCommandRunner._update_changed_files(dk_api, rl['different'], kitchen, recipe_name, message, dryrun)
        if not rc.ok():
            return rc
        msg_differences = rc.get_message()

        rc = DKCloudCommandRunner._add_new_files(dk_api, rl['only_local'], kitchen, recipe_name, message, dryrun)
        if not rc.ok():
            return rc
        msg_additions = rc.get_message()

        rc = DKCloudCommandRunner._remove_deleted_files(dk_api, rl['only_remote'], kitchen, recipe_name, message,
                                                        dryrun)
        if not rc.ok():
            return rc
        msg_deletions = rc.get_message()

        msg = ''
        if len(msg_differences) > 0:
            if len(msg) > 0:
                msg += '\n'
            msg += msg_differences + '\n'
        if len(msg_additions) > 0:
            if len(msg) > 0:
                msg += '\n'
            msg += msg_additions + '\n'
        if len(msg_deletions) > 0:
            if len(msg) > 0:
                msg += '\n'
            msg += msg_deletions + '\n'
        rc.set_message(msg)
        return rc

    @staticmethod
    def _remove_deleted_files(dk_api, deleted_files, kitchen, recipe_name, message, dryrun=False):
        msg = ''
        ig = DKIgnore()
        files_to_delete = list()
        folders_to_delete = list()
        for folder_path, folder_contents in deleted_files.items():
            if ig.ignore(folder_path):
                continue
            if len(folder_contents) == 0:
                folders_to_delete.append(folder_path)
            else:
                for file_to_delete in folder_contents:
                    file_path = os.path.join(os.sep.join(folder_path.split(os.sep)[1:]), file_to_delete['filename'])
                    files_to_delete.append(file_path)

        tree_rc = dk_api.recipe_tree(kitchen, recipe_name)
        if tree_rc.ok():
            recipe_tree = tree_rc.get_payload()
            for folder_to_delete in folders_to_delete:
                if folder_to_delete in recipe_tree:
                    files_in_folder = recipe_tree[folder_to_delete]
                    for file_to_delete in files_in_folder:
                        file_path = os.path.join(os.sep.join(folder_to_delete.split(os.sep)[1:]),
                                                 file_to_delete['filename'])
                        files_to_delete.append(file_path)
        else:
            msg += 'Unable to delete files in some folders %s' % "".join([str(x) for x in folders_to_delete])

        if len(files_to_delete) > 0:
            tabbed_file_names = list()
            for file_to_delete in files_to_delete:
                tabbed_file_names.append('\t' + file_to_delete)
                if not dryrun:
                    rc = DKCloudCommandRunner.delete_file(dk_api, kitchen, recipe_name, message, file_to_delete)
                    if not rc.ok():
                        rc.set_message(msg + '\n' + rc.get_message())
                        return rc

            if dryrun:
                header_msg = '%d files will be deleted:\n' % len(files_to_delete)
            else:
                header_msg = '%d files deleted:\n' % len(files_to_delete)

            tabbed_file_names.sort()
            msg = header_msg + '\n'.join(tabbed_file_names)

        rc = DKReturnCode()
        rc.set(DKReturnCode.DK_SUCCESS, msg)
        return rc

    @staticmethod
    def _add_files_in_folder(dk_api, start_folder, kitchen, recipe_name, message, dryrun=False):

        msg = ''
        ig = DKIgnore()
        files_found = [os.path.join(start_folder, fn) for fn in next(os.walk(start_folder))[2]]
        for this_file in files_found:
            if ig.ignore(this_file):
                continue
            if dryrun:
                msg += 'File to be created: %s \n' % this_file
            else:
                rc = DKCloudCommandRunner.add_file(dk_api, kitchen, recipe_name, message, this_file)
                if not rc.ok():
                    rc.set_message(msg + '\n' + rc.get_message())
                    return rc
                msg += rc.get_message() + '\n'

    @staticmethod
    def _add_new_files(dk_api, new_files, kitchen, recipe_name, message, dryrun=False):
        msg = ''
        ig = DKIgnore()

        files_to_add = list()
        for folder_path, folder_contents in new_files.items():
            folder_path_wo_recipe = os.sep.join(folder_path.split(os.sep)[1:])
            if ig.ignore(folder_path):
                continue

            if len(folder_contents) == 0:
                # We shouldn't expect any folders to be added it should just be list of files.
                files_found = [os.path.join(folder_path_wo_recipe, fn) for fn in
                               next(os.walk(folder_path_wo_recipe))[2]]
                if len(files_found) > 0:
                    files_to_add.extend(files_found)
            else:
                for new_file in folder_contents:
                    local_file_path = os.path.join(folder_path_wo_recipe, new_file['filename'])
                    if ig.ignore(local_file_path):
                        continue
                    files_to_add.append(local_file_path)

        tabbed_file_names = list()
        for file_to_add in files_to_add:
            tabbed_file_names.append('\t' + file_to_add)
            if not dryrun:
                rc = DKCloudCommandRunner.add_file(dk_api, kitchen, recipe_name, message, file_to_add)
                if not rc.ok():
                    rc.set_message(msg + '\n' + rc.get_message())
                    return rc

        if len(files_to_add) > 0:
            if dryrun:
                header_msg = '%d files will be added:\n' % len(files_to_add)
            else:
                header_msg = '%d files added:\n' % len(files_to_add)

            tabbed_file_names.sort()
            msg = header_msg + '\n'.join(tabbed_file_names)

        rc = DKReturnCode()
        rc.set(DKReturnCode.DK_SUCCESS, msg)
        return rc

    @staticmethod
    def _update_changed_files(dk_api, changed_files, kitchen, recipe_name, message, dryrun=False):
        msg = ''
        ig = DKIgnore()
        updated_file_count = 0
        tabbed_file_names = list()
        for folder_path, folder_contents in changed_files.items():
            if ig.ignore(folder_path):
                continue
            if len(folder_contents) == 0:
                # Not expecting an entire directory of files to update. The updates should be on a file by file basis.
                raise
            else:
                for changed_file in folder_contents:
                    local_file = os.path.join(os.sep.join(folder_path.split(os.sep)[1:]), changed_file['filename'])
                    if ig.ignore(local_file):
                        continue
                    updated_file_count += 1
                    tabbed_file_names.append('\t' + local_file)
                    if not dryrun:
                        rc = DKCloudCommandRunner.update_file(dk_api, kitchen, recipe_name, message, local_file)
                        if not rc.ok():
                            rc.set_message(msg + '\n' + rc.get_message())
                            return rc

        if updated_file_count > 0:
            if dryrun:
                msg_header = '%d files will be updated:\n' % updated_file_count
            else:
                msg_header = '%d files updated:\n' % updated_file_count

            tabbed_file_names.sort()
            msg = msg_header + '\n'.join(tabbed_file_names)

        rc = DKReturnCode()
        rc.set(DKReturnCode.DK_SUCCESS, msg)
        return rc

    @staticmethod
    @check_api_param_decorator
    def update_file(dk_api, kitchen, recipe_name, message, files_to_update_param):
        """
        reutrns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string  -- kitchen name, string
        :param message: string message -- commit message, string
        :param files_to_update_param: string  -- file system directory where the recipe file lives
        :rtype: string
        """
        rc = DKReturnCode()
        if kitchen is None or recipe_name is None or message is None or files_to_update_param is None:
            s = 'ERROR: DKCloudCommandRunner bad input parameters'
            rc.set(rc.DK_FAIL, s)
            return rc

        # Take a simple string or an array
        if isinstance(files_to_update_param, str):
            files_to_update = [files_to_update_param]
        else:
            files_to_update = files_to_update_param

        msg = ''
        for file_to_update in files_to_update:
            try:
                with open(file_to_update, 'r') as f:
                    file_contents = f.read()
            except IOError as e:
                if len(msg) != 0:
                    msg += '\n'
                msg += '%s' % (str(e))
                rc.set(rc.DK_FAIL, msg)
                return rc
            except ValueError as e:
                if len(msg) != 0:
                    msg += '\n'
                msg += 'ERROR: %s' % e.message
                rc.set(rc.DK_FAIL, msg)
                return rc
            rc = dk_api.update_file(kitchen, recipe_name, message, file_to_update, file_contents)
            if not rc.ok():
                if len(msg) != 0:
                    msg += '\n'
                msg += 'DKCloudCommand.update_file for %s failed\n\tmessage: %s' % (file_to_update, rc.get_message())
                rc.set_message(msg)
                return rc
            else:
                if len(msg) != 0:
                    msg += '\n'
                msg += 'DKCloudCommand.update_file for %s succeeded' % file_to_update

        rc.set_message(msg)
        return rc

    @staticmethod
    @check_api_param_decorator
    def add_file(dk_api, kitchen, recipe_name, message, api_file_key):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string
        :param message: string  -- commit message, string
        :param api_file_key: string  -- directory where the recipe file lives
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if kitchen is None or recipe_name is None or message is None or api_file_key is None:
            s = 'ERROR: DKCloudCommandRunner bad input parameters'
            rc.set(rc.DK_FAIL, s)
            return rc

        ig = DKIgnore()
        if ig.ignore(api_file_key):
            rs = 'DKCloudCommand.add_file ignoring %s' % api_file_key
            rc.set_message(rs)
            return rc

        if not os.path.exists(api_file_key):
            s = "'%s' does not exist" % api_file_key
            rc.set(rc.DK_FAIL, s)
            return rc

        try:
            with open(api_file_key, 'r') as f:
                file_contents = f.read()
        except ValueError as e:
            s = 'ERROR: %s' % e.message
            rc.set(rc.DK_FAIL, s)
            return rc
        rc = dk_api.add_file(kitchen, recipe_name, message, api_file_key, file_contents)
        if rc.ok():
            rs = 'DKCloudCommand.add_file for %s succeed' % api_file_key
        else:
            rs = 'DKCloudCommand.add_file for %s failed\nmessage: %s' % (api_file_key, rc.get_message())
        rc.set_message(rs)
        return rc

    @staticmethod
    @check_api_param_decorator
    def delete_file(dk_api, kitchen, recipe_name, message, files_to_delete_param):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string  -- kitchen name, string
        :param message: string message -- commit message, string
        :param files_to_delete_param: path to the files to delete
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if kitchen is None or recipe_name is None or message is None or files_to_delete_param is None:
            s = 'ERROR: DKCloudCommandRunner bad input parameters'
            rc.set(rc.DK_FAIL, s)
            return rc

        # Take a simple string or an array
        if isinstance(files_to_delete_param, str):
            files_to_delete = [files_to_delete_param]
        else:
            files_to_delete = files_to_delete_param
        msg = ''
        for file_to_delete in files_to_delete:
            basename = os.path.basename(file_to_delete)
            rc = dk_api.delete_file(kitchen, recipe_name, message, file_to_delete, basename)
            if not rc.ok():
                msg += '\nDKCloudCommand.delete_file for %s failed\nmessage: %s' % (file_to_delete, rc.get_message())
                rc.set_message(msg)
                return rc
            else:
                msg += 'DKCloudCommand.delete_file for %s succeed' % file_to_delete
        rc.set_message(msg)
        return rc

    @staticmethod
    @check_api_param_decorator
    def watch_active_servings(dk_api, kitchen, period):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param period: integer
        :rtype: string
        """
        print('period', period)

        # try:
        #     p = int(period)
        # except ValueError:
        #     return 'DKCloudCommand.watch_active_servings requires an integer for the period'
        if period <= 0:
            return 'DKCloudCommand.watch_active_servings requires a positive period'

        DKActiveServingWatcherSingleton().set_sleep_time(period)
        DKActiveServingWatcherSingleton().set_api(dk_api)
        DKActiveServingWatcherSingleton().set_kitchen(kitchen)
        DKActiveServingWatcherSingleton().start_watcher()
        return ""

    # http://stackoverflow.com/questions/19652446/python-program-with-thread-cant-catch-ctrlc
    @staticmethod
    def join_active_serving_watcher_thread_join():
        # print 'Start join_active_serving_watcher_thread_join'
        if DKActiveServingWatcherSingleton().get_watcher().get_run_thread() is not None:
            try:
                DKActiveServingWatcherSingleton().get_watcher().get_run_thread().join(1)
            except Exception as e:
                print('join_active_serving_watcher_thread_join %s' % str(e))

    @staticmethod
    def stop_watcher():
        DKActiveServingWatcherSingleton().stop_watcher()

    @staticmethod
    def watcher_running():
        return DKActiveServingWatcherSingleton().should_run()

    @staticmethod
    @check_api_param_decorator
    def get_compiled_serving(dk_api, kitchen, recipe_name, variation_name):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string  -- kitchen name, string
        :param variation_name: string -- name of the recipe variation_name to be used
        :rtype: DKReturnCode
        """
        rc = dk_api.get_compiled_serving(kitchen, recipe_name, variation_name)
        if rc.ok():
            rs = 'DKCloudCommand.get_compiled_serving succeeded %s\n' % json.dumps(rc.get_payload(), indent=4)
        else:
            m = rc.get_message()
            e = m.split('the logfile errors are:nn')
            if len(e) > 1:
                e2 = DKCloudCommandRunner._decompress(e[len(e) - 1])
                errors = e2.split('|')
                re = e[0] + " " + 'the logfile errors are: '
                for e in errors:
                    re += '\n%s' % e
            else:
                re = m
            rs = 'DKCloudCommand.get_compiled_serving failed\nmessage: %s\n' % re
        rc.set_message(rs)
        return rc

    @staticmethod
    def resolve_conflict(file_path):
        recipe_name = DKRecipeDisk.find_recipe_name()
        recipe_meta_dir = DKKitchenDisk.get_recipe_meta_dir(recipe_name)
        recipe_root_dir = DKRecipeDisk.find_recipe_root_dir()
        file_full_path = os.path.join(os.getcwd(), file_path)
        fixed = DKRecipeDisk.resolve_conflict(recipe_meta_dir, recipe_root_dir, file_full_path)
        rc = DKReturnCode()
        if fixed:
            rc.set(DKReturnCode.DK_SUCCESS, 'Conflict resolved for %s in recipe %s' % (file_path, recipe_name))
        else:
            rc.set(DKReturnCode.DK_FAIL,
                   'Error: Unable to resolve conflict for %s in recipe %s' % (file_path, recipe_name))
        return rc

    @staticmethod
    def _print_unresolved_conflicts(unresolved_conflicts):
        msg = 'There are unresolved conflicts\n'
        for recipe_name, recipe_conflicts in unresolved_conflicts.items():
            if len(recipe_conflicts) != 0:
                msg += "\tUnresolved conflicts for recipe '%s'\n" % recipe_name
            for recipe_folder, folder_contents in recipe_conflicts.items():
                for conflict_key, conflict_info in folder_contents.items():
                    msg += '\t\t%s/%s\n' % (conflict_info['folder_in_recipe'], conflict_info['filename'])
        return msg

    @staticmethod
    def get_unresolved_conflicts(recipe_name, recipe_dir):
        rc = DKReturnCode()
        unresolved_conflicts = DKKitchenDisk.get_unresolved_conflicts(None, None, recipe_dir)
        if unresolved_conflicts is not None and len(unresolved_conflicts) != 0:
            msg = DKCloudCommandRunner._print_unresolved_conflicts(unresolved_conflicts)
            rc.set(DKReturnCode.DK_SUCCESS, msg)
            return rc
        else:
            rc.set(DKReturnCode.DK_SUCCESS, 'No conflicts found.')
            return rc

    @staticmethod
    @check_api_param_decorator
    def merge_kitchens_improved(dk_api, from_kitchen, to_kitchen):
        """
        returns a string.
        :param dk_api: -- api object
        :param from_kitchen: string
        :param to_kitchen: string  -- kitchen name, string
        :rtype: DKReturnCode
        """
        unresolved_conflicts = DKKitchenDisk.get_unresolved_conflicts(from_kitchen, to_kitchen)
        if unresolved_conflicts is not None and len(unresolved_conflicts) != 0:
            msg = DKCloudCommandRunner._print_unresolved_conflicts(unresolved_conflicts)
            rc = DKReturnCode()
            rc.set(DKReturnCode.DK_FAIL, msg)
            return rc

        resolved_conflicts = DKKitchenDisk.get_resolved_conflicts(from_kitchen, to_kitchen)
        # if resolved_conflicts is not None and len(resolved_conflicts) != 0:

        md = dk_api.merge_kitchens_improved(from_kitchen, to_kitchen, resolved_conflicts)
        if not md.ok():
            md.set_message('merge_kitchens_improved error from %s to Kitchen %s\nmessage: %s' %
                           (from_kitchen, to_kitchen, md.get_message()))
            return md
        merge_no_conflicts = DKCloudCommandRunner._check_no_merge_conflicts(md.get_payload())
        if merge_no_conflicts:
            msg = DKCloudCommandRunner._print_merge_success(md.get_payload())
            current_kitchen = DKKitchenDisk.find_kitchen_name()
            md.set_message(msg)
        else:
            # Found conflicts
            recipe_name = DKRecipeDisk.find_recipe_name()
            kitchen_name = DKKitchenDisk.find_kitchen_name()
            if recipe_name is None and kitchen_name is None:
                # We are not in a kitchen or recipe folder, so just report the findings
                rs = DKCloudCommandRunner.print_merge_conflicts(md.get_payload())
                md.set_message(rs)
            else:
                # We are in a recipe folder, so let's write out the conflicted files.
                rc = DKCloudCommandRunner.write_merge_conflicts(md.get_payload())
                if rc.ok():
                    md.set_message(rc.get_message())
                else:
                    md = rc
        return md

    @staticmethod
    def write_recipe_merge_conflicts(merge_info, recipe_name_param, kitchen_dir):
        rc = DKReturnCode()
        if recipe_name_param not in merge_info['conflicts']:
            rc.set(rc.DK_FAIL,
                   "DKCloudCommandRunner.write_recipe_merge_conflicts: Can't find conflicts for recipe %s." % recipe_name_param)
            return rc
        recipe_conflicts = merge_info['conflicts'][recipe_name_param]
        for folder_name, folder_contents in recipe_conflicts.items():
            folder_fullpath = os.path.join(kitchen_dir, folder_name)
            for conflict in folder_contents:
                file_fullpath = os.path.join(folder_fullpath, conflict['filename'])
                if 'conflict_tags' in conflict:
                    with open(file_fullpath, 'w') as conflict_file:
                        conflict_file.write(base64.b64decode(conflict['conflict_tags']))
                    if not DKRecipeDisk.add_conflict_to_conflicts_meta(conflict, folder_name, recipe_name_param,
                                                                       kitchen_dir):
                        rc.set(rc.DK_FAIL,
                               "DKCloudCommandRunner.write_recipe_merge_conflicts: Unable to write out conflict meta for %s" % file_fullpath)
                        return rc
                else:
                    rc.set(rc.DK_FAIL,
                           "DKCloudCommandRunner.write_recipe_merge_conflicts: Can't find conflict tags for %s" % file_fullpath)
                    return rc

        rc.set(rc.DK_SUCCESS, "Conflicts for recipe %s written to %s\n" % (
            recipe_name_param, os.path.join(kitchen_dir, recipe_name_param)))
        return rc

    @staticmethod
    def write_merge_conflicts(payload):
        # If in kitchen directory, write out the conflicts for the recipes that we have local
        # If in recipe directory, write out the conflicts for that recipe only.
        rc = DKReturnCode()
        kitchen_dir = DKKitchenDisk.find_kitchen_root_dir()
        if kitchen_dir is None:
            rc.set(rc.DK_FAIL,
                   "DKCloudCommandRunner.write_merge_conflicts: This operation only available under a kitchen")
            return rc
        local_recipes = DKKitchenDisk.find_available_recipes(kitchen_dir)
        if len(local_recipes) == 0:
            msg = DKCloudCommandRunner.print_merge_conflicts(payload)
            rc.set(rc.DK_SUCCESS, "No recipe folder found in disk.\n" + msg)
            return rc

        # Make sure all of the recipes that have conflicts are local on disk. If not, get them.
        merge_info = payload['merge-kitchen-result']['merge_info']
        recipes_not_local = []
        for conflict_recipe_name in merge_info['conflicts']:
            found_recipe = next((recipe for recipe in local_recipes if recipe == conflict_recipe_name), None)
            if not found_recipe:
                recipes_not_local.append(conflict_recipe_name)

        if len(recipes_not_local) != 0:
            msg = "DKCloudCommandRunner.write_merge_conflicts: The recipes %s were not found locally."
            msg += " Call recipe-get from the kitchen folder %s, then rerun the merge."
            rc.set(rc.DK_FAIL, msg % (recipes_not_local, kitchen_dir))
            return rc

        for recipe in local_recipes:
            recipe_rc = DKCloudCommandRunner.write_recipe_merge_conflicts(merge_info, recipe, kitchen_dir)
            if not recipe_rc.ok():
                return recipe_rc

        msg = DKCloudCommandRunner.print_merge_conflicts(payload)
        rc.set(rc.DK_SUCCESS, msg + "Conflicts written to disk\n")
        return rc

    @staticmethod
    def print_merge_conflicts(payload):
        # Either the merge succeeded or there was nothing to do.
        if 'conflicts' in payload['merge-kitchen-result']['merge_info']:
            conflicts = payload['merge-kitchen-result']['merge_info']['conflicts']
            msg = ''
            file_count = 0
            for recipe_name, recipe_folders in conflicts.items():
                for recipe_folder_name, recipe_folder in recipe_folders.items():
                    msg += "\tConflicted files in recipe '%s'\n" % recipe_folder_name
                    for this_file in recipe_folder:
                        msg += "\t\t%s\n" % os.path.join(recipe_folder_name, this_file['filename'])
                        file_count += 1

            if file_count == 1:
                conflict_msg = 'conflict'
            else:
                conflict_msg = 'conflicts'
            msg = '%d %s found\n' % (file_count, conflict_msg) + msg
            return msg
        return ''

    @staticmethod
    def _print_merge_success(payload):
        # Either the merge succeeded or there was nothing to do.
        merge_info = payload['merge-kitchen-result']['merge_info']
        msg = ''
        if merge_info['merge_status'] == 204:
            msg += merge_info['message'] + '\n'
            return msg

        files_changed = 0
        field_names = ['filename', 'number_of_changes', 'changes_viz']
        x = PrettyTable()
        x.field_names = field_names
        x.set_style(PLAIN_COLUMNS)
        x.header = False
        x.align["filename"] = "l"
        x.align["number_of_changes"] = "r"
        x.align["changes_viz"] = "l"
        x.left_padding_width = 1
        for recipe_name, recipe_folders in merge_info['recipes'].items():
            for folder_name, files_in_folder in recipe_folders.items():
                for this_file in files_in_folder:
                    row = [this_file['filename'], this_file['changes'],
                           '%s%s' % ('+' * int(this_file['additions']), '-' * int(this_file['deletions']))]
                    x.add_row(row)
                    files_changed += 1
        msg += x.get_string() + '\n'
        msg += '%d files changed, %d insertions(+), %d deletions(-)' % (
            files_changed, merge_info['stats']['additions'], merge_info['stats']['deletions'])
        return msg

    # --------------------------------------------------------------------------------------------------------------------
    #  Order commands
    # --------------------------------------------------------------------------------------------------------------------    @staticmethod
    @staticmethod
    @check_api_param_decorator
    def create_order(dk_api, kitchen, recipe_name, variation_name, node_name=None):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param recipe_name: string  -- kitchen name, string
        :param variation_name: string -- name of the recipe variation_name to be run
        :param node_name: string -- name of the single node to run
        :rtype: DKReturnCode
        """
        rc = dk_api.create_order(kitchen, recipe_name, variation_name, node_name)
        if rc.ok():
            s = 'Order ID is: %s' % rc.get_payload()
        else:
            m = rc.get_message().replace('\\n','\n')
            e = m.split('the logfile errors are:')
            if len(e) > 1:
                e2 = DKCloudCommandRunner._decompress(e[-1])
                errors = e2.split('|')
                re = e[0] + " " + 'the logfile errors are: '
                for e in errors:
                    re += '\n%s' % e
            else:
                re = m
            s = 'DKCloudCommand.create_order failed\nmessage: %s\n' % re
        rc.set_message(s)
        return rc


    @staticmethod
    @check_api_param_decorator
    def order_resume(dk_api, orderrun_id):

        rc = dk_api.order_resume(orderrun_id)

        if not rc.ok():
            rc.set_message(
                'order_resume error. unable to resume orderrun %s\nmessage: %s' % (
                    orderrun_id, rc.get_message()))
        else:
            payload = rc.get_payload()
            rc.set_message('DKCloudCommand.order_resume %s succeeded\n' % orderrun_id)
        return rc


    @staticmethod
    @check_api_param_decorator
    def delete_one_order(dk_api, order_id):
        kl = dk_api.order_delete_one(order_id)
        if kl.ok():
            kl.set_message('deleted order %s\n' % order_id)
        else:
            kl.set_message('unable to delete order id %s\nmessage: %s' % (order_id, kl.get_message()))
        return kl

    @staticmethod
    @check_api_param_decorator
    def stop_order(dk_api, order_id):
        kl = dk_api.order_stop(order_id)
        if kl.ok():
            kl.set_message('stopped order %s\n' % order_id)
        else:
            kl.set_message('unable to stop order id %s\nmessage: %s' % (order_id, kl.get_message()))
        return kl

    @staticmethod
    @check_api_param_decorator
    def stop_orderrun(dk_api, orderrun_id):
        kl = dk_api.orderrun_stop(orderrun_id)
        if kl.ok():
            kl.set_message('stopped order run %s\n' % orderrun_id)
        else:
            kl.set_message('unable to stop order run id %s\nmessage: %s' % (orderrun_id, kl.get_message()))
        return kl

    @staticmethod
    @check_api_param_decorator
    def delete_all_order(dk_api, kitchen):
        kl = dk_api.order_delete_all(kitchen)
        if kl.ok():
            kl.set_message('deleted kitchen %s\n' % kitchen)
        else:
            kl.set_message('unable to delete orders in kitchen %s\nmessage: %s' % (kitchen, kl.get_message()))
        return kl

    @staticmethod
    @check_api_param_decorator
    def orderrun_detail(dk_api, kitchen, pd):
        """
        returns a string.
        :param dk_api: -- api object
        :param kitchen: string
        :param pd: dict
        :rtype: DKReturnCode
        """
        if DKCloudCommandRunner.SUMMARY in pd:
            display_summary = True
        else:
            display_summary = False
        # always get summary information
        pd[DKCloudCommandRunner.SUMMARY] = True
        rc = dk_api.orderrun_detail(kitchen, pd)
        s = ''
        if not rc.ok() or not isinstance(rc.get_payload(), list):
            s = 'Issue with getting order run details\nmessage: %s' % rc.get_message()
            rc.set_message(s)
            return rc

        # we have a list of servings, find the right dict
        serving_list = rc.get_payload()
        serving = None
        if DKCloudCommandRunner.ORDER_RUN_ID in pd:
            order_run_id = pd[DKCloudCommandRunner.ORDER_RUN_ID]
            for serv in serving_list:
                if serv[DKCloudCommandRunner.ORDER_RUN_ID] == order_run_id:
                    serving = serv
                    break
        elif DKCloudCommandRunner.ORDER_ID in pd:
            order_id = pd[DKCloudCommandRunner.ORDER_ID]
            for serv in serving_list:
                if serv[DKCloudCommandRunner.ORDER_ID] == order_id:
                    serving = serv
                    break
        else:
            # find the newest serving
            dex = -1
            latest = None
            for i, serving in enumerate(serving_list):
                if DKCloudCommandRunner.ORDER_ID in serving and serving[DKCloudCommandRunner.ORDER_ID] > latest:
                    latest = serving[DKCloudCommandRunner.ORDER_ID]
                    dex = i
            if dex != -1:
                serving = serving_list[dex]

        if serving is None:
            rc.set(rc.DK_FAIL,
                   "No OrderRun information.  Try using 'dk order-list -k %s' to see what is available." % kitchen)
            return rc

        # serving now contains the dictionary of the serving to display
        # pull out the information and put it in the message string of the rc

        if serving and display_summary:
            s += '\nORDER RUN SUMMARY\n\n'
            summary = None
            if DKCloudCommandRunner.SUMMARY in serving:
                summary = serving[DKCloudCommandRunner.SUMMARY]
            pass
            s += 'Order ID:\t%s\n' % serving[DKCloudCommandRunner.ORDER_ID]
            orid_from_serving = serving[DKCloudCommandRunner.ORDER_RUN_ID]
            s += 'Order Run ID:\t%s\n' % orid_from_serving
            s += 'Status:\t\t%s\n' % serving['status']
            s += 'Kitchen:\t%s\n' % kitchen

            if summary and 'name' in summary:
                s += 'Recipe:\t\t%s\n' % summary['name']
            else:
                s += 'Recipe:\t\t%s\n' % 'Not available'

            # variation name is inside the order id, pull it out
            s += 'Variation:\t%s\n' % orid_from_serving.split('#')[3]

            if summary and 'start-time' in summary:
                start_time = summary['start-time']
                if isinstance(start_time, str):
                    s += 'Start time:\t%s\n' % summary['start-time'].split('.')[0]
                else:
                    s += 'Start time:\t%s\n' % 'Not available 1'
            else:
                s += 'Start time:\t%s\n' % 'Not available 2'

            run_time = None
            if summary and 'total-recipe-time' in summary:
                run_time = summary['total-recipe-time']
            if isinstance(run_time, str):  # Active recipes don't have a run-duration
                s += 'Run duration:\t%s (H:M:S)\n' % run_time.split('.')[0]
            else:
                s += 'Run duration:\t%s\n' % 'Not available'

        if serving and DKCloudCommandRunner.TESTRESULTS in serving and \
                isinstance(serving[DKCloudCommandRunner.TESTRESULTS], str):
            s += '\nTEST RESULTS'
            s += serving[DKCloudCommandRunner.TESTRESULTS]
        if serving and DKCloudCommandRunner.TIMINGRESULTS in serving and \
                isinstance(serving[DKCloudCommandRunner.TIMINGRESULTS], str):
            s += '\n\nTIMING RESULTS\n\n'
            s += serving[DKCloudCommandRunner.TIMINGRESULTS]
        if serving and DKCloudCommandRunner.LOGS in serving and \
                isinstance(serving[DKCloudCommandRunner.LOGS], str):
            s += '\n\nLOG\n\n'
            s += DKCloudCommandRunner._decompress(serving[DKCloudCommandRunner.LOGS])
        if 'status' in pd and serving and DKCloudCommandRunner.SUMMARY in serving and \
                isinstance(serving[DKCloudCommandRunner.SUMMARY], dict):
            s += '\nSTEP STATUS\n\n'
            summary = serving[DKCloudCommandRunner.SUMMARY]
            # loop through the sorted keys
            for key in sorted(summary):
                value = summary[key]
                if isinstance(value, dict):
                    # node/step info is stored as a dictionary, print the node name (key) and status
                    if 'status' in value:
                        status = value['status']
                    else:
                        status = 'unknown'
                    s += '%s\t%s\n' % (key, status)

        if serving and 'runstatus' in pd:
            s += serving['status']

        if serving and 'disp_order_id' in pd and DKCloudCommandRunner.ORDER_ID in serving:
            s += serving[DKCloudCommandRunner.ORDER_ID]

        if serving and 'disp_order_run_id' in pd and DKCloudCommandRunner.ORDER_RUN_ID in serving:
            s += serving[DKCloudCommandRunner.ORDER_RUN_ID]

        rc.set_message(s)
        return rc

    @staticmethod
    def parse_serving_id(serving_id):
        serving_mesos_id_parts = serving_id.split('#')
        rv = dict()
        rv['mesos_job_number'] = serving_mesos_id_parts[0]
        rv['recipe'] = serving_mesos_id_parts[2]
        rv['variation'] = serving_mesos_id_parts[3]
        rv['kitchen'] = serving_mesos_id_parts[4]
        rv['chronos_job_number'] = serving_mesos_id_parts[5]
        return rv

    @staticmethod
    def parse_order_id(order_id):
        serving_chronos_id_parts = order_id.split('#')
        rv = dict()
        rv['recipe'] = serving_chronos_id_parts[2]
        rv['variation'] = serving_chronos_id_parts[3]
        rv['kitchen'] = serving_chronos_id_parts[4]
        rv['chronos_job_number'] = serving_chronos_id_parts[5]
        return rv

    @staticmethod
    @check_api_param_decorator
    def list_order(dk_api, kitchen):
        """
        """
        rc = dk_api.list_order(kitchen)
        if not rc.ok():
            s = 'DKCloudCommand.list_order failed\nmessage: %s' % rc.get_message()
            rc.set_message(s)
            return rc

        rows = []
        payload = rc.get_payload()

        for order in payload['orders']:
            # Found an order without any servings. Add it to the list.
            if order['serving_chronos_id'] is not None:
                order_info = DKCloudCommandRunner.parse_order_id(order['serving_chronos_id'])
                serving_list = list()
                for serving in payload['servings']:
                    if serving['serving_chronos_id'] == order['serving_chronos_id']:
                        serving_list.append(serving)
                order = [
                    order['serving_chronos_id'],
                    order_info['recipe'],
                    order_info['variation'],
                    order['chronos-status'],
                    order['schedule'] if 'schedule' in order else '',
                    serving_list]
                rows.append(order)

        s = ''
        for order in rows:
            s += DKCloudCommandRunner._display_order_summary(order, kitchen)
            count = 1
            for serving in order[5]:
                s += DKCloudCommandRunner._display_serving_summary(serving, count)
                count += 1
            rc.set_message(s)

        return rc

    @staticmethod
    @check_api_param_decorator
    def delete_orderrun(dk_api, orderrun_id):
        """
        """
        rc = dk_api.delete_orderrun(orderrun_id)
        if not rc.ok():
            rc.set_message(
                'delete_orderrun error. unable to delete orderrun %s\nmessage: %s' % (
                    orderrun_id, rc.get_message()))
        else:
            payload = rc.get_payload()
            rc.set_message('DKCloudCommand.delete_orderrun %s succeeded\n' % orderrun_id)
        return rc


    # Helpers
    @staticmethod
    def _display_order_summary(order_info_list, kitchen):
        s= ""
        s += '\nORDER SUMMARY (order ID: '
        s += '%s)\n' % order_info_list[0]
        s += 'Kitchen:\t%s\n' % kitchen
        s += 'Recipe:\t\t%s\n' % order_info_list[1]
        s += 'Variation:\t%s\n' % order_info_list[2]
        s += 'Schedule:\t%s\n' % order_info_list[4]
        s += 'Status:\t\t%s\n' % order_info_list[3]
        return s

    @staticmethod
    def _display_serving_summary(serving, number=-1):
        s= ""
        if number > 0:
            s += '\n  %d.  ORDER RUN\t(OrderRun ID: ' %  number
        else:
            s += '\n  ORDER RUN\t(OrderRun ID: '

        orid_from_serving = serving[DKCloudCommandRunner.ORDER_RUN_ID]
        s += '%s)\n' % orid_from_serving
        if 'orderrun_status' in serving:
            s += '\tOrderRun Status %s\n' % serving['orderrun_status']
        else:
            s += '\tStatus:\t\t%s\n' % serving['status']
            
        if serving and 'timings' in serving and 'start-time' in serving['timings']:
            start_time = serving['timings']['start-time']
            if isinstance(start_time, str):
                s += '\tStart time:\t%s\n' % start_time.split('.')[0]
            else:
                s += '\tStart time:\t%s\n' % 'Not available 1'
        else:
            s += '\tStart time:\t%s\n' % 'Not available 2'

        if serving and 'timings' in serving and 'end-time' in serving['timings']:
            end_time = serving['timings']['end-time']
            if isinstance(end_time, str):
                s += '\tEnd time:\t%s\n' % end_time.split('.')[0]
            else:
                s += '\tEnd time:\t%s\n' % 'Not available'
        else:
            s += '\tEnd time:\t%s\n' % 'Not available 2'

        if serving and 'timings' in serving and 'duration' in serving['timings']:
            duration = serving['timings']['duration']
            if isinstance(duration, str):
                s += '\tDuration:\t%s (H:M:S)\n' % duration.split('.')[0]
            else:
                s += '\tDuration:\t%s\n' % 'Not available'
        else:
            s += '\tDuration:\t%s\n' % 'Not available 2'
        return s

    @staticmethod
    def _get_serving_top_line(serving):
        recipe_name = kitchen_name = serving_id = status = 'unknown'
        if DKCloudCommandRunner.RECIPENAME in serving:
            recipe_name = serving[DKCloudCommandRunner.RECIPENAME]
        if DKCloudCommandRunner.SERVINGID in serving:
            serving_id = serving[DKCloudCommandRunner.SERVINGID]
        if DKCloudCommandRunner.KITCHEN in serving:
            kitchen_name = serving[DKCloudCommandRunner.KITCHEN]
        if DKCloudCommandRunner.STATE in serving:
            status = serving[DKCloudCommandRunner.STATE]
        return 'Recipe (%s) in Kitchen(%s) with Status(%s) and OrderRun Id(%s)' % \
               (recipe_name, kitchen_name, status, serving_id)

    @staticmethod
    def _dump_serving_statuses(rc, the_type):
        rs = ''
        for serving in rc[the_type]:
            if isinstance(serving, dict) is True and DKCloudCommandRunner.STATUSES in serving:
                rs += 'Status for %s\n' % DKCloudCommandRunner._get_serving_top_line(serving)
                rs += serving[DKCloudCommandRunner.STATUSES]
                rs += '\n'
        return rs

    @staticmethod
    def _dump_serving_logs(rc, the_type):
        rs = ''
        for serving in rc[the_type]:
            if isinstance(serving, dict) is True and DKCloudCommandRunner.LOGS in serving:
                rs += 'Log Files for %s \n' % DKCloudCommandRunner._get_serving_top_line(serving)
                if serving[DKCloudCommandRunner.LOGS] is not None and len(serving[DKCloudCommandRunner.LOGS]) > 0:
                    try:
                        rs += DKCloudCommandRunner._decompress(serving[DKCloudCommandRunner.LOGS])
                    except (ValueError, TypeError):
                        rs += 'unable to decomoress log file'
                else:
                    rs += 'no log file'
                rs += '\n'
        return rs

    @staticmethod
    def _dump_serving_tests(rc, the_type):
        rs = ''
        for serving in rc[the_type]:
            if isinstance(serving, dict) is True and DKCloudCommandRunner.TESTRESULTS in serving:
                rs += 'Test Results for %s\n' % DKCloudCommandRunner._get_serving_top_line(serving)
                rs += serving[DKCloudCommandRunner.TESTRESULTS]
                rs += '\n'
        return rs

    @staticmethod
    def _dump_serving_summary(rc, the_type, as_string=False):
        rs = ''
        for serving in rc[the_type]:
            if isinstance(serving, dict) is True and DKCloudCommandRunner.SUMMARY in serving:
                if as_string is True:
                    rs += 'Test Results for %s\n' % DKCloudCommandRunner._get_serving_top_line(serving)
                    rs += json.dumps(serving[DKCloudCommandRunner.SUMMARY], indent=4)
                    rs += '\n'
                else:
                    return serving[DKCloudCommandRunner.SUMMARY]
        return rs

    @staticmethod
    def _dump_serving_timings(rc, the_type):
        rs = ''
        for serving in rc[the_type]:
            if isinstance(serving, dict) is True and DKCloudCommandRunner.TIMINGRESULTS in serving:
                rs += 'TIming Results for %s\n' % DKCloudCommandRunner._get_serving_top_line(serving)
                rs += serving[DKCloudCommandRunner.TIMINGRESULTS]
                rs += '\n'
        return rs

    @staticmethod
    def _check_no_merge_conflicts(resp):
        if isinstance(resp, dict) and 'merge-kitchen-result' in resp and 'status' in resp['merge-kitchen-result'] \
                and resp['merge-kitchen-result']['status'] == 'success':
            return True
        else:
            return False

    @staticmethod
    def _split_one_end(path):
        """
        Utility function for splitting off the very end part of a path.
        """
        s = path.rsplit('/', 1)
        if len(s) == 1:
            return s[0], ''
        else:
            return tuple(s)

    # @staticmethod
    # def _print_merge_patches(merge_conflicts):
    #     rs = ''
    #     from_kitchen = merge_conflicts['from-kitchen-name']
    #     mkr = merge_conflicts['merge-kitchen-result']
    #     if mkr['status'] != 'diverged':
    #         return
    #     for recipe_name, v in mkr.iteritems():
    #         if recipe_name != 'status':
    #             # rs += '\nRecipe: %s\n' % recipe_name
    #             for directory, payload in v.iteritems():
    #                 for difference in payload:
    #                     if difference['to_kitchen'] == from_kitchen:
    #                         rs += 'File: %s\n' % os.path.join(directory, difference['filename'])
    #                         # rs += '%s\n' % difference['patch']
    #     return rs

    @staticmethod
    def _compress(the_input):
        if isinstance(the_input, str):
            return base64.b64encode(zlib.compress(the_input, 9))
        else:
            raise ValueError('compress requires string input')

    @staticmethod
    def _decompress(the_input):
        if isinstance(the_input, str):
            return zlib.decompress(base64.b64decode(the_input))
        else:
            raise ValueError('decompress requires string input')

    @staticmethod
    def _print_test_results(r):
        return 'File'
