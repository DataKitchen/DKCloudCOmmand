
class DKIgnore(object):

    _defaults = ['.DS_Store', '.dk']
    _defaults_file_name = 'dkignore_default.txt'
    _ignore_these = []

    def __init__(self):

        tmp_defaults = list()
        try:
            with open(self._defaults_file_name, 'r') as defaults_file:
                tmp_defaults = defaults_file.read().splitlines().strip()
        except IOError:
            # print 'Unable to open %s' % self._defaults_file_name
            pass

        for ignore_me in tmp_defaults:
            if ignore_me[0] != '#':
                self._defaults.append(ignore_me)

        self._ignore_these = list(self._defaults)

    def ignore(self, check_item):
        matches = next((item for item in self._ignore_these if item in check_item), None)
        if matches is None:
            return False
        else:
            return True

    def add_ignore(self, ignore_this_item):
        self._ignore_these.append(ignore_this_item)