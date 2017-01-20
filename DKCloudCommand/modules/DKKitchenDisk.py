import os

KITCHEN_META = 'KITCHEN_META'
DK_DIR = '.dk'
DK_RECIPES_META_DIR = 'recipes'


class DKKitchenDisk:
    def __init__(self):
        pass

    @staticmethod
    def check_kitchen_folder(kitchen_name, root_dir):
        kitchen_dir = os.path.join(root_dir, kitchen_name)
        # Is the directory empty?
        for root, subdirs, files in os.walk(kitchen_dir):
            if len(subdirs) != 0 or len(files) != 0:
                return False
        return True

    @staticmethod
    def create_kitchen_meta_dir(kitchen_dir):
        kitchen_meta_dir = os.path.join(kitchen_dir, DK_DIR)
        if not os.path.exists(kitchen_meta_dir):
            os.makedirs(kitchen_meta_dir)
        DKKitchenDisk.create_recipes_meta_dir(kitchen_meta_dir)
        return kitchen_meta_dir

    @staticmethod
    def create_recipes_meta_dir(kitchen_meta_dir):
        recipes_meta_dir = os.path.join(kitchen_meta_dir, DK_RECIPES_META_DIR)
        if not os.path.isdir(recipes_meta_dir):
            try:
                os.makedirs(recipes_meta_dir)
            except OSError as e:
                print "%s - %s - %s" % (e.filename, e.errno, e.message)
                return None
        return recipes_meta_dir

    @staticmethod
    def get_recipe_meta_dir(recipe_name, start_dir=None):
        recipes_meta = DKKitchenDisk.get_recipes_meta_dir(start_dir)
        if recipes_meta is None:
            return None
        recipe_meta = os.path.join(recipes_meta, recipe_name)
        return recipe_meta

    @staticmethod
    def get_recipes_meta_dir(start_dir=None):
        kitchen_meta_dir = DKKitchenDisk.find_kitchen_meta_dir(start_dir)
        if kitchen_meta_dir is None:
            return None
        return os.path.join(kitchen_meta_dir, DK_RECIPES_META_DIR)

    @staticmethod
    def get_unresolved_conflicts(from_kitchen, to_kitchen, start_dir=None):
        recipes = DKKitchenDisk.find_available_recipes(start_dir)
        if recipes is None:
            return None

        from DKRecipeDisk import DKRecipeDisk
        all_unresolved = {}
        for recipe in recipes:
            recipe_meta_dir = DKKitchenDisk.get_recipe_meta_dir(recipe, start_dir)
            unresolved = DKRecipeDisk.get_unresolved_conflicts_meta(recipe_meta_dir, from_kitchen, to_kitchen)
            if len(unresolved) != 0:
                all_unresolved[recipe] = unresolved
        return all_unresolved

    @staticmethod
    def get_resolved_conflicts(from_kitchen, to_kitchen, start_dir=None):
        recipes = DKKitchenDisk.find_available_recipes(start_dir)
        if recipes is None:
            return None

        from DKRecipeDisk import DKRecipeDisk
        all_resolved = {}
        for recipe in recipes:
            recipe_meta_dir = DKKitchenDisk.get_recipe_meta_dir(recipe, start_dir)
            resolved = DKRecipeDisk.get_resolved_conflicts_meta(recipe_meta_dir, from_kitchen, to_kitchen)
            if len(resolved) != 0:
                all_resolved[recipe] = resolved
        return all_resolved

    @staticmethod
    def write_kitchen(kitchen_name, root_dir):
        kitchen_dir = os.path.join(root_dir, kitchen_name)
        if not os.path.exists(kitchen_dir):
            os.makedirs(kitchen_dir)
        plug_dir = DKKitchenDisk.create_kitchen_meta_dir(kitchen_dir)
        with open(os.path.join(plug_dir, KITCHEN_META), 'w') as kitchen_file:
            kitchen_file.write(kitchen_name)
        return True

    @staticmethod
    def find_kitchen_meta_dir(walk_dir=None):
        return DKKitchenDisk._find_kitchen(walk_dir, return_meta_path=True)

    @staticmethod
    def find_kitchen_root_dir(walk_dir=None):
        rv = DKKitchenDisk._find_kitchen(walk_dir, return_meta_path=True)
        if rv is None:
            return None
        else:
            parts = os.path.split(rv)
            return parts[0]

    @staticmethod
    def find_kitchen_name(walk_dir=None):
        return DKKitchenDisk._find_kitchen(walk_dir, return_meta_path=False)

    @staticmethod
    def is_kitchen_root_dir(walk_dir=None):
        rv = DKKitchenDisk._find_kitchen(walk_dir, recurse=False)
        if rv is None:
            return False
        else:
            return True

    @staticmethod
    def find_available_recipes(walk_dir=None):
        meta_dir = DKKitchenDisk.find_kitchen_meta_dir(walk_dir)
        if meta_dir is None:
            return None

        recipes_dir = DKKitchenDisk.get_recipes_meta_dir(meta_dir)
        recipe_names = next(os.walk(recipes_dir))[1]
        return recipe_names

    @staticmethod
    def _find_kitchen(walk_dir=None, return_meta_path=False, recurse=True):

        if walk_dir is None:
            walk_dir = os.getcwd()

        if not os.path.isdir(walk_dir):
            return None

        subdirs = next(os.walk(walk_dir))[1]
        if DK_DIR in subdirs:
            try:
                with open(os.path.join(walk_dir, DK_DIR, KITCHEN_META), 'r') as k:
                    kitchen_name = k.read()
                if kitchen_name is not None and len(kitchen_name) > 0:
                    if return_meta_path:
                        return os.path.join(walk_dir, DK_DIR)
                    else:
                        return kitchen_name
                else:
                    # Maybe throw an error here. The .dk folder is in a bad state
                    return None
            except IOError:
                print "No KITCHEN_META found in '%s'" % (os.path.join(walk_dir, DK_DIR))
                return None
        else:
            if recurse:
                parts = os.path.split(walk_dir)
                if len(parts) != 2:
                    return None
                else:
                    if parts[0] != walk_dir:
                        return DKKitchenDisk._find_kitchen(parts[0], return_meta_path=return_meta_path)
                    else:
                        # We are at the top of the directory structure.
                        # There was nothing to tokenize out
                        return None
            else:
                return None
