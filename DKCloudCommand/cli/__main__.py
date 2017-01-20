#!/usr/bin/env python

import click
import os
from sys import path, exit
import sys
from os.path import expanduser
from signal import signal, SIGUSR1, SIGQUIT, SIGINT, getsignal, pause
from datetime import datetime

__author__ = 'DataKitchen, Inc.'

home = expanduser('~')  # does not end in a '/'
if os.path.join(home, 'dev/DKCloudCommand') not in path:
    path.insert(0, os.path.join(home, 'dev/DKCloudCommand'))
from DKCloudCommand.modules.DKCloudAPI import DKCloudAPI
from DKCloudCommand.modules.DKCloudCommandConfig import DKCloudCommandConfig
from DKCloudCommand.modules.DKCloudCommandRunner import DKCloudCommandRunner
from DKCloudCommand.modules.DKKitchenDisk import DKKitchenDisk
from DKCloudCommand.modules.DKRecipeDisk import DKRecipeDisk

DK_VERSION = '1.0.10'

alias_exceptions = {'recipe-conflicts': 'rf', 'kitchen-config': 'kf', 'recipe-create': 're'}

class Backend(object):
    _short_commands = {}

    def __init__(self, config_path_param=None):
        if config_path_param is None:
            if os.environ.get('DKCLI_CONFIG_LOCATION') is not None:
                config_file_location = os.path.expandvars('${DKCLI_CONFIG_LOCATION}').strip()
            else:
                config_file_location = home + "/dev/DKCloudCommand/DKCloudCommand/DKCloudCommandConfig.json"
        else:
            config_file_location = config_path_param

        if not os.path.isfile(config_file_location):
            raise click.ClickException("Config file '%s' not found" % config_file_location)

        cfg = DKCloudCommandConfig()
        if not cfg.init_from_file(config_file_location):
            s = "Unable to load configuration from '%s'" % config_file_location
            raise click.ClickException(s)
        self.dki = DKCloudAPI(cfg)
        if self.dki is None:
            s = 'Unable to create and/or connect to backend object.'
            raise click.ClickException(s)
        token = self.dki.login()
        if token is None:
            s = 'login failed'
            raise click.ClickException(s)

    @staticmethod
    def get_kitchen_name_soft(given_kitchen=None):
        """
        Get the kitchen name if it is available.
        :return: kitchen name or None
        """
        if given_kitchen is not None:
            return given_kitchen
        else:
            in_kitchen = DKCloudCommandRunner.which_kitchen_name()
            return in_kitchen

    @staticmethod
    def check_in_kitchen_root_folder_and_get_name():
        """
        Ensures that the caller is in a kitchen folder.
        :return: kitchen name or None
        """
        in_kitchen = DKCloudCommandRunner.which_kitchen_name()
        if in_kitchen is None:
            raise click.ClickException("Please change directory to a kitchen folder.")
        else:
            return in_kitchen

    @staticmethod
    def get_kitchen_from_user(kitchen=None):
        in_kitchen = DKCloudCommandRunner.which_kitchen_name()
        if kitchen is None and in_kitchen is None:
            raise click.ClickException("You must provide a kitchen name or be in a kitchen folder.")
        elif kitchen is not None and in_kitchen is not None:
            raise click.ClickException(
                    "Please provide a kitchen parameter or change directory to a kitchen folder, not both.\nYou are in Kitchen '%s'" % in_kitchen)

        if in_kitchen is not None:
            use_kitchen = in_kitchen
        else:
            use_kitchen = kitchen
        return "ok", use_kitchen

    @staticmethod
    def get_recipe_name(recipe):
        in_recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None and in_recipe is None:
            raise click.ClickException("You must provide a recipe name or be in a recipe folder.")
        elif recipe is not None and in_recipe is not None:
            raise click.ClickException(
                    "Please provide a recipe parameter or change directory to a recipe folder, not both.\nYou are in Recipe '%s'" % in_recipe)

        if in_recipe is not None:
            use_recipe = in_recipe
        else:
            use_recipe = recipe
        return "ok", use_recipe

    def set_short_commands(self, commands):
        short_commands = {}
        for long_command in commands:
            if long_command in alias_exceptions:
                short_commands[long_command] = alias_exceptions[long_command]
                continue
            parts = long_command.split('-')
            short_command = ''
            for part in parts:
                if part == 'orderrun':
                    short_command += 'or'
                else:
                    short_command += part[0]
            short_commands[long_command] = short_command
        self._short_commands = short_commands
        return self._short_commands

    def get_short_commands(self):
        return self._short_commands


def check_and_print(rc):
    if rc.ok():
        click.echo(rc.get_message())
    else:
        raise click.ClickException(rc.get_message())


class AliasedGroup(click.Group):

    # def format_commands(self, ctx, formatter):
    #     #super(AliasedGroup, self).format_commands(ctx, formatter)
    #     """Extra format methods for multi methods that adds all the commands
    #     after the options.
    #     """
    #     rows = []
    #     for subcommand in self.list_commands(ctx):
    #         cmd = self.get_command(ctx, subcommand)
    #         # What is this, the tool lied about a command.  Ignore it
    #         if cmd is None:
    #             continue
    #
    #         help = cmd.short_help or ''
    #         rows.append((subcommand, help))
    #
    #     if rows:
    #         with formatter.section('Commands'):
    #             formatter.write_dl(rows)
    #
    #         with formatter.section('ShortCommands'):
    #             formatter.write_dl(rows)

    def get_command(self, ctx, cmd_name):
        self._check_unique(ctx)
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        found_command = next(
            (long_command for long_command, short_command in alias_exceptions.items() if short_command == cmd_name),
            None)

        if found_command is not None:
            return click.Group.get_command(self, ctx, found_command)

        all_commands = self.list_commands(ctx)
        for long_command in all_commands:
            short_command = self.short_command(long_command)
            if short_command == cmd_name:
                return click.Group.get_command(self, ctx, long_command)
        ctx.fail("Unable to find command for alias '%s'" % cmd_name)

    def short_command(self,long_command):
        if long_command in alias_exceptions:
            return alias_exceptions[long_command]
        parts = long_command.split('-')
        short_command = ''
        for part in parts:
            if part == 'orderrun':
                short_command += 'or'
            else:
                short_command += part[0]
        return short_command

    def _check_unique(self, ctx):
        all_commands = self.list_commands(ctx)
        short_commands = {}
        for long_command in all_commands:
            if long_command in alias_exceptions:
                continue

            short_command = self.short_command(long_command)

            if short_command in short_commands:
                click.secho("The short alias %s is not ambiguous" % short_command, fg='red')
            else:
                short_commands[short_command] = long_command

    def format_commands(self, ctx, formatter):
        # override default behavior
        rows = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue

            help = cmd.short_help or ''
            rows.append(('%s (%s)' % (subcommand, self.short_command(subcommand)), help))

        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)


@click.group(cls=AliasedGroup)
@click.option('--config', '-c', type=str, required=False, help='Path to config file')
@click.version_option(version=DK_VERSION)
@click.pass_context
def dk(ctx, config):
    ctx.obj = Backend(config)
    ctx.obj.set_short_commands(ctx.command.commands)
    # token = ctx.obj.dki._auth_token
    # if token is None:
    #     exit(1)


# Use this to override the automated help
class DKClickCommand(click.Command):
    def __init__(self, name, context_settings=None, callback=None,
                 params=None, help=None, epilog=None, short_help=None,
                 options_metavar='[OPTIONS]', add_help_option=True):
        super(DKClickCommand, self).__init__(name, context_settings, callback,
                                             params, help, epilog, short_help,
                                             options_metavar, add_help_option)

    def get_help(self, ctx):
        # my_help = click.Command.get_help(ctx)
        my_help = super(DKClickCommand, self).get_help(ctx)
        return my_help


@dk.command(name='config-list', cls=DKClickCommand)
@click.pass_obj
def config_list(backend):
    """
    Print the current configuration
    """
    click.secho('Print Configuration', fg='green')
    print str(backend.dki.get_config())


@dk.command(name='recipe-status')
@click.pass_obj
def recipe_status(backend):
    """
    Compare local recipe to remote recipe for the current recipe.
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe_name = DKRecipeDisk.find_recipe_name()
    click.secho("%s - Getting the status of Recipe '%s' in Kitchen '%s'\n\tversus directory '%s'" % (
        get_datetime(), recipe_name, kitchen, recipe_dir), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_status(backend.dki, kitchen, recipe_name, recipe_dir))


@dk.command(name='recipe-conflicts')
@click.pass_obj
def recipe_conflicts(backend):
    """
    See if there are any unresolved conflicts for this recipe.
    """
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder.')
    recipe_name = DKRecipeDisk.find_recipe_name()
    click.secho("%s - Checking for conflicts on Recipe '%s'" % (
        get_datetime(),recipe_name))
    recipe_name = DKRecipeDisk.find_recipe_name()
    check_and_print(DKCloudCommandRunner.get_unresolved_conflicts(recipe_name, recipe_dir))


# --------------------------------------------------------------------------------------------------------------------
# User and Authentication Commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='user-info')
@click.pass_obj
def user_info(backend):
    """
    Get information about this user.
    """
    check_and_print(DKCloudCommandRunner.user_info(backend.dki))


# --------------------------------------------------------------------------------------------------------------------
#  kitchen commands
# --------------------------------------------------------------------------------------------------------------------
def get_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@dk.command(name='kitchen-list')
@click.pass_obj
def kitchen_list(backend):
    """
    List all Kitchens
    """
    click.echo(click.style('%s - Getting the list of kitchens' % get_datetime(), fg='green'))
    check_and_print(DKCloudCommandRunner.list_kitchen(backend.dki))


@dk.command(name='kitchen-get')
@click.option('--recipe', '-r', type=str, multiple=True, help='Get the recipe along with the kitchen. Multiple allowed')
@click.argument('kitchen_name', required=True)
@click.pass_obj
def kitchen_get(backend, kitchen_name, recipe):
    """
    Get an existing Kitchen
    """
    found_kitchen = DKKitchenDisk.find_kitchen_name()
    if found_kitchen is not None and len(found_kitchen) > 0:
        raise click.ClickException("You cannot get a kitchen into an existing kitchen directory structure.")

    if len(recipe) > 0:
        click.secho("%s - Getting kitchen '%s' and the recipes %s" % (get_datetime(), kitchen_name, str(recipe)), fg='green')
    else:
        click.secho("%s - Getting kitchen '%s'" % (get_datetime(), kitchen_name), fg='green')

    check_and_print(DKCloudCommandRunner.get_kitchen(backend.dki, kitchen_name, os.getcwd(), recipe))


@dk.command(name='kitchen-which')
@click.pass_obj
def kitchen_which(backend):
    """
    What Kitchen am I working in?
    """
    check_and_print(DKCloudCommandRunner.which_kitchen(backend.dki, None))


@dk.command(name='kitchen-create')
@click.argument('kitchen', required=True)
@click.option('--parent', '-p', type=str, required=True, help='name of parent kitchen')
@click.pass_obj
def kitchen_create(backend, parent, kitchen):
    """
    Create a new kitchen
    """
    click.secho('%s - Creating kitchen %s from parent kitchen %s' % (get_datetime(), kitchen, parent), fg='green')
    master = 'master'
    if kitchen.lower() != master.lower():
        check_and_print(DKCloudCommandRunner.create_kitchen(backend.dki, parent, kitchen))
    else:
        raise click.ClickException('Cannot create a kitchen called %s' % master)


@dk.command(name='kitchen-delete')
@click.argument('kitchen', required=True)
@click.pass_obj
def kitchen_delete(backend, kitchen):
    """
    Provide the name of the kitchen to delete
    """
    click.secho('%s - Deleting kitchen %s' % (get_datetime(), kitchen), fg='green')
    master = 'master'
    if kitchen.lower() != master.lower():
        check_and_print(DKCloudCommandRunner.delete_kitchen(backend.dki, kitchen))
    else:
        raise click.ClickException('Cannot delete the kitchen called %s' % master)


@dk.command(name='kitchen-config')
@click.option('--kitchen', '-k', type=str, required=False, help='kitchen name')
@click.option('--add', '-a', type=str, required=False, nargs=2,
              help='Add a new override to this kitchen. This will update an existing override variable.',
              multiple=True)
@click.option('--get', '-g', type=str, required=False, help='Get the value for an override variable.', multiple=True)
@click.option('--unset', '-u', type=str, required=False, help='Delete an override variable.', multiple=True)
@click.option('--listall', '-l', type=str, is_flag=True, required=False, help='List all variables and their values.')
@click.pass_obj
def kitchen_config(backend, kitchen, add, get, unset, listall):
    """
    Get and Set Kitchen variable overrides
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    check_and_print(DKCloudCommandRunner.config_kitchen(backend.dki, use_kitchen, add, get, unset, listall))


@dk.command(name='kitchen-merge')
@click.option('--source_kitchen', '-s', type=str, required=True, help='source (from) kitchen name')
@click.option('--target_kitchen', '-t', type=str, required=True, help='target (to) kitchen name')
@click.pass_obj
def kitchen_merge(backend, source_kitchen, target_kitchen):
    """
    Merge two Kitchens
    """
    click.secho('%s - Merging Kitchen %s into Kitchen %s' % (get_datetime(), source_kitchen, target_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.merge_kitchens_improved(backend.dki, source_kitchen, target_kitchen))


# --------------------------------------------------------------------------------------------------------------------
#  Recipe commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='recipe-list')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.pass_obj
def recipe_list(backend, kitchen):
    """
    List the Recipes in a Kitchen
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho("%s - Getting the list of Recipes for Kitchen '%s'" % (get_datetime(), use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.list_recipe(backend.dki, use_kitchen))

@dk.command(name='recipe-create')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.argument('name', required=True)
@click.pass_obj
def recipe_create(backend, kitchen, name):
    """
    Create a new Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho("%s - Creating Recipe %s for Kitchen '%s'" % (get_datetime(), name, use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_create(backend.dki, use_kitchen,name))

@dk.command(name='recipe-get')
@click.argument('recipe', required=False)
@click.pass_obj
def recipe_get(backend, recipe):
    """
    Get the latest files for this recipe.
    """
    recipe_root_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_root_dir is None:
        if recipe is None:
            raise click.ClickException("\nPlease change to a recipe folder or provide a recipe name arguement")

        # raise click.ClickException('You must be in a Recipe folder')
        kitchen_root_dir = DKKitchenDisk.is_kitchen_root_dir()
        if not kitchen_root_dir:
            raise click.ClickException("\nPlease change to a recipe folder or a kitchen root dir.")
        recipe_name = recipe
        start_dir = DKKitchenDisk.find_kitchen_root_dir()
    else:
        recipe_name = DKRecipeDisk.find_recipe_name()
        if recipe is not None:
            if recipe_name != recipe:
                raise click.ClickException("\nThe recipe name argument '%s' is inconsistent with the current directory '%s'" % (recipe, recipe_root_dir))
        start_dir = recipe_root_dir

    kitchen_name = Backend.get_kitchen_name_soft()
    click.secho("%s - Getting the latest version of Recipe '%s' in Kitchen '%s'" % (get_datetime(), recipe_name, kitchen_name), fg='green')
    check_and_print(DKCloudCommandRunner.get_recipe(backend.dki, kitchen_name, recipe_name, start_dir))


# @dk.command(name='recipe-cook')
# @click.argument('variation', required=True)
# @click.option('--kitchen', '-k', type=str, help='kitchen name')
# @click.option('--recipe', '-r', type=str, help='recipe name')
# @click.pass_obj
# def recipe_cook(backend, kitchen, recipe, variation):
#     """
#     Cook a given variation for a Recipe in a Kitchen
#     """
#     err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
#     if use_kitchen is None:
#         click.ClickException(err_str)
#     if recipe is None:
#         recipe = DKRecipeDisk.find_recipe_name()
#         if recipe is None:
#             raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')
#
#     click.secho('Cooking Recipe %s.%s in Kitchen %s' % (recipe, variation, use_kitchen), fg='green')
#     check_and_print(DKCloudCommandRunner.cook_recipe(backend.dki, use_kitchen, recipe, variation))


@dk.command(name='recipe-compile')
@click.option('--variation', '-v', type=str, required=True, help='variation name')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.pass_obj
def recipe_compile(backend, kitchen, recipe, variation):
    """
    Apply variables to a Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)

    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Get the Compiled OrderRun of Recipe %s.%s in Kitchen %s' % (get_datetime(), recipe, variation, use_kitchen),
                fg='green')
    check_and_print(DKCloudCommandRunner.get_compiled_serving(backend.dki, use_kitchen, recipe, variation))


# --------------------------------------------------------------------------------------------------------------------
#  File commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='file-add')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--message', '-m', type=str, required=True, help='add message')
@click.argument('filepath', required=True)
@click.pass_obj
def file_add(backend, kitchen, recipe, message, filepath):
    """
    Add a newly created file to a Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Adding File (%s) to Recipe (%s) in kitchen(%s) with message (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.add_file(backend.dki, use_kitchen, recipe, message, filepath))


@dk.command(name='file-update')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def file_update(backend, kitchen, recipe, message, filepath):
    """
    Update a Recipe file
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Updating File(s) (%s) in Recipe (%s) in Kitchen(%s) with message (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.update_file(backend.dki, use_kitchen, recipe, message, filepath))


@dk.command(name='recipe-update')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.option('--dryrun', '-d', default=False, is_flag=True, required=False, help='just display changed files')
@click.pass_obj
def file_update_all(backend, message, dryrun):
    """
    Update all of the changed files for this Recipe
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You must be in a Kitchen')
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe = DKRecipeDisk.find_recipe_name()

    if dryrun:
        click.secho('%s - Display all changed files in Recipe (%s) in Kitchen(%s) with message (%s)' %
                    (get_datetime(), recipe, kitchen, message), fg='green')
    else:
        click.secho('%s - Updating all changed files in Recipe (%s) in Kitchen(%s) with message (%s)' %
                    (get_datetime(), recipe, kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.update_all_files(backend.dki, kitchen, recipe, recipe_dir, message, dryrun))


@dk.command(name='file-delete')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def file_delete(backend, kitchen, recipe, message, filepath):
    """
    Delete a Recipe file. Provide the file name and path to the file name, relative to the recipe root
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Deleting (%s) in Recipe (%s) in kitchen(%s) with message (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.delete_file(backend.dki, use_kitchen, recipe, message, filepath))


@dk.command(name='file-resolve')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def file_resolve(backend, filepath):
    """
    Mark a conflicted file as resolved, so that a merge can be completed
    """
    recipe = DKRecipeDisk.find_recipe_name()
    if recipe is None:
        raise click.ClickException('You must be in a recipe folder.')

    click.secho("%s - Resolving conflicts" % get_datetime())

    for file_to_resolve in filepath:
        if not os.path.exists(file_to_resolve):
            raise click.ClickException('%s does not exist' % file_to_resolve)
        check_and_print(DKCloudCommandRunner.resolve_conflict(file_to_resolve))

# --------------------------------------------------------------------------------------------------------------------
#  Active Serving commands
# --------------------------------------------------------------------------------------------------------------------

@dk.command(name='active-serving-watcher')
@click.argument('kitchen', required=False)
@click.option('--period', '-p', type=int, required=False, default=5, help='watching period, in seconds')
@click.pass_obj
def active_serving_watcher(backend, kitchen, period):
    """
    Watches all cooking Recipes in a Kitchen
    Provide the kitchen name as an argument or be in a Kitchen folder.
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho('%s - Watching Active OrderRun Changes in Kitchen %s' % (get_datetime(), use_kitchen), fg='green')
    DKCloudCommandRunner.watch_active_servings(backend.dki, use_kitchen, period)
    while True:
        try:
            DKCloudCommandRunner.join_active_serving_watcher_thread_join()
            if not DKCloudCommandRunner.watcher_running():
                break
        except KeyboardInterrupt:
            print 'KeyboardInterrupt'
            exit_gracefully(None, None)
    exit(0)


# --------------------------------------------------------------------------------------------------------------------
#  Order commands
# --------------------------------------------------------------------------------------------------------------------

@dk.command(name='order-run')
@click.argument('variation', required=True)
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--node', '-n', type=str, required=False, help='Name of the node to run')
@click.pass_obj
def order_run(backend, kitchen, recipe, variation, node):
    """
    Run an order: cook a recipe variation
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    msg = '%s - Create an Order:\n\tKitchen: %s\n\tRecipe: %s\n\tVariation: %s\n' % (get_datetime(), use_kitchen, recipe, variation)
    if node is not None:
        msg += '\tNode: %s\n' % node

    click.secho(msg, fg='green')
    check_and_print(DKCloudCommandRunner.create_order(backend.dki, use_kitchen, recipe, variation, node))


@dk.command(name='order-delete')
@click.option('--kitchen', '-k', type=str, default=None, help='kitchen name')
@click.option('--order_id', '-o', type=str, default=None, help='Order ID')
@click.pass_obj
def order_delete(backend, kitchen, order_id):
    """
    Delete one order or all orders in a kitchen
    """
    use_kitchen = Backend.get_kitchen_name_soft(kitchen)
    print use_kitchen
    if use_kitchen is None and order_id is None:
        raise click.ClickException('You must specify either a kitchen or an order_id or be in a kitchen directory')

    if order_id is not None:
        click.secho('%s - Delete an Order using id %s' % (get_datetime(), order_id), fg='green')
        check_and_print(DKCloudCommandRunner.delete_one_order(backend.dki, order_id))
    else:
        click.secho('%s - Delete all orders in Kitchen %s' % (get_datetime(), use_kitchen), fg='green')
        check_and_print(DKCloudCommandRunner.delete_all_order(backend.dki, use_kitchen))


@dk.command(name='order-stop')
@click.option('--order_id', '-o', type=str, required=True, help='Order ID')
@click.pass_obj
def order_stop(backend, order_id):
    """
    Stop an order - Turn off the serving generation ability of an order.  Stop any running jobs.  Keep all state around.
    """
    if order_id is None:
        raise click.ClickException('invalid order id %s' % order_id)
    click.secho('%s - Stop order id %s' % (get_datetime(), order_id), fg='green')
    check_and_print(DKCloudCommandRunner.stop_order(backend.dki, order_id))


@dk.command(name='orderrun-stop')
@click.option('--order_run_id', '-r', type=str, required=True, help='OrderRun ID')
@click.pass_obj
def order_stop(backend, order_run_id):
    """
    Stop the run of an order - Stop the running order and keep all state around.
    """
    if order_run_id is None:
        raise click.ClickException('invalid order id %s' % order_run_id)

    click.secho('%s - Stop order id %s' % (get_datetime(), order_run_id), fg='green')
    check_and_print(DKCloudCommandRunner.stop_orderrun(backend.dki, order_run_id.strip()))


@dk.command(name='orderrun-info')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--order_id', '-o', type=str, default=None, help='Order ID')
@click.option('--order_run_id', '-r', type=str, default=None, help='OrderRun ID to display')
@click.option('--summary', '-s', default=False, is_flag=True, required=False, help='display run summary information')
@click.option('--nodestatus', '-n', default=False, is_flag=True, required=False, help=' display node status info')
@click.option('--log', '-l', default=False, is_flag=True, required=False, help=' display log info')
@click.option('--timing', '-t', default=False, is_flag=True, required=False, help='display timing results')
@click.option('--test', '-q', default=False, is_flag=True, required=False, help='display test results')
@click.option('--runstatus', default=False, is_flag=True, required=False,
              help=' display status of the run (single line)')
@click.option('--disp_order_id', default=False, is_flag=True, required=False,
              help=' display the order id (single line)')
@click.option('--disp_order_run_id', default=False, is_flag=True, required=False,
              help=' display the order run id (single line)')
@click.option('--all_things', '-a', default=False, is_flag=True, required=False, help='display all information')
# @click.option('--recipe', '-r', type=str, help='recipe name')
@click.pass_obj
def orderrun_detail(backend, kitchen, summary, nodestatus, runstatus, log, timing, test, all_things,
                    order_id, order_run_id, disp_order_id, disp_order_run_id):
    """
    Display information about an Order-Run
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    # if recipe is None:
    #     recipe = DKRecipeDisk.find_reciper_name()
    #     if recipe is None:
    #         raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')
    pd = dict()
    if all_things:
        pd['summary'] = True
        pd['logs'] = True
        pd['timingresults'] = True
        pd['testresults'] = True
        # pd['state'] = True
        pd['status'] = True
    if summary:
        pd['summary'] = True
    if log:
        pd['logs'] = True
    if timing:
        pd['timingresults'] = True
    if test:
        pd['testresults'] = True
    if nodestatus:
        pd['status'] = True

    if runstatus:
        pd['runstatus'] = True
    if disp_order_id:
        pd['disp_order_id'] = True
    if disp_order_run_id:
        pd['disp_order_run_id'] = True

    # if the user does not specify anything to display, show the summary information
    if not runstatus and \
            not all_things and \
            not test and \
            not timing and \
            not log and \
            not nodestatus and \
            not summary and \
            not disp_order_id and \
            not disp_order_run_id:
        pd['summary'] = True

    if order_id is not None and order_run_id is not None:
        raise click.ClickException("Cannot specify both the Order Id and the OrderRun Id")
    if order_id is not None:
        pd[DKCloudCommandRunner.ORDER_ID] = order_id.strip()
    elif order_run_id is not None:
        pd[DKCloudCommandRunner.ORDER_RUN_ID] = order_run_id.strip()

    # don't print the green thing if it is just runstatus
    if not runstatus and not disp_order_id and not disp_order_run_id:
        click.secho('%s - Display Order-Run details from kitchen %s' % (get_datetime(), use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.orderrun_detail(backend.dki, use_kitchen, pd))


@dk.command('orderrun-delete')
@click.argument('orderrun_id', required=True)
@click.pass_obj
def delete_orderrun(backend, orderrun_id):
    """
    Delete the orderrun specified by the argument.
    """
    click.secho('%s - Deleting orderrun %s' % (get_datetime(), orderrun_id), fg='green')
    check_and_print(DKCloudCommandRunner.delete_orderrun(backend.dki, orderrun_id.strip()))


@dk.command('orderrun-resume')
@click.argument('orderrun_id', required=True)
@click.pass_obj
def order_resume(backend, orderrun_id):
    """
    Resumes a failed order run
    """
    click.secho('%s - Resuming orderrun %s' % (get_datetime(), orderrun_id), fg='green')
    check_and_print(DKCloudCommandRunner.order_resume(backend.dki, orderrun_id.strip()))


@dk.command(name='order-list')
@click.option('--kitchen', '-k', type=str, required=False, help='Filter results for kitchen only')

@click.pass_obj
def order_list(backend, kitchen):
    """
    Apply variables to a Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)


    click.secho('%s - Get Order information for Kitchen %s' % (get_datetime(), use_kitchen), fg='green')

    check_and_print(
            DKCloudCommandRunner.list_order(backend.dki, use_kitchen))

# --------------------------------------------------------------------------------------------------------------------
#  Secret commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='secret-list')
@click.argument('path', required=False)
@click.pass_obj
def secret_list(backend,path):
    """
    List all Secrets
    """
    click.echo(click.style('%s - Getting the list of secrets' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_list(backend.dki,path))

@dk.command(name='secret-write')
@click.argument('entry',required=True)
@click.pass_obj
def secret_write(backend,entry):
    """
    Write a secret
    """
    path,value=entry.split('=')

    if value.startswith('@'):
        with open(value[1:]) as vfile:
            value = vfile.read()

    click.echo(click.style('%s - Writing secret' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_write(backend.dki,path,value))

@dk.command(name='secret-delete')
@click.argument('path', required=True)
@click.pass_obj
def secret_delete(backend,path):
    """
    Delete a secret
    """
    click.echo(click.style('%s - Deleting secret' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_delete(backend.dki,path))

@dk.command(name='secret-exists')
@click.argument('path', required=True)
@click.pass_obj
def secret_delete(backend,path):
    """
    Checks if a secret exists
    """
    click.echo(click.style('%s Checking secret' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_exists(backend.dki,path))

# http://stackoverflow.com/questions/18114560/python-catch-ctrl-c-command-prompt-really-want-to-quit-y-n-resume-executi
def exit_gracefully(signum, frame):
    # print 'exit_gracefully'
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    DKCloudCommandRunner.stop_watcher()
    # print 'exit_gracefully stopped watcher'
    signal(SIGINT, original_sigint)
    question = False
    if question is True:
        try:
            if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
                exit(1)
        except (KeyboardInterrupt, SystemExit):
            print("Ok ok, quitting")
            exit(1)
    else:
        print("Ok ok, quitting now")
        DKCloudCommandRunner.join_active_serving_watcher_thread_join()
        exit(1)
    # restore the exit gracefully handler here
    signal(SIGINT, exit_gracefully)


# https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # store the original SIGINT handler
    original_sigint = getsignal(SIGINT)
    signal(SIGINT, exit_gracefully)
    dk()


# if __name__ == '__main__':
#     # store the original SIGINT handler
#     original_sigint = getsignal(SIGINT)
#     signal(SIGINT, exit_gracefully)
#     dk()

if __name__ == "__main__":
    main()
