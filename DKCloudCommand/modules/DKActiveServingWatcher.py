from threading import Thread
import time
from sys import stdout
from DKCloudAPI import DKCloudAPI
from DKReturnCode import *
DK_ACTIVE_SERVING_WATCHER_SLEEP_TIME = 5


class DKActiveServingWatcherSingleton(object):
    __shared_state = {}
    watcher = None
    keep_running = True
    sleep_time = DK_ACTIVE_SERVING_WATCHER_SLEEP_TIME

    def __init__(self):
        self.__dict__ = self.__shared_state
        if self.watcher is None:
            self.watcher = DKActiveServingWatcher()

    def start_watcher(self):
        self.keep_running = True
        return self.watcher.start_watcher()

    def wait_until_watcher_complete(self):
        self.watcher.wait_until_watcher_complete()

    def get_watcher(self):
        return self.watcher

    def get_sleep_time(self):
        return self.sleep_time

    def set_sleep_time(self, st):
        self.sleep_time = st

    def set_api(self, api):
        self.watcher.set_api(api)

    def set_kitchen(self, kitchen_name):
        self.watcher.set_kitchen(kitchen_name)

    def should_run(self):
        return self.keep_running

    def stop_watcher(self):
        self.keep_running = False

    def print_serving_summary(self, serving):
        self.watcher.print_serving_summary(serving)


# Only one watcher runs  ... run and done.
def make_watcher_thread(watcher, *args):
    if watcher is None or isinstance(watcher, DKActiveServingWatcher) is False:
        print 'make_watcher_thread bad watcher'
        return
    #print 'Starting watcher make thread'
    while DKActiveServingWatcherSingleton().should_run() is True:
        #print ' calling watcher.watch()'
        watcher.watch()
        time.sleep(DKActiveServingWatcherSingleton().get_sleep_time())
    #print 'Ending watcher make thread 2'


class DKActiveServingWatcher(object):
    _time = 'last-update-time'

    def __init__(self, api=None, kn=None):
        self.run_thread = None
        self._api = api
        self._kitchen_name = kn

    def get_run_thread(self):
        return self.run_thread

    def set_api(self, api):
        self._api = api

    def set_kitchen(self, kitchen_name):
        self._kitchen_name = kitchen_name

    def start_watcher(self):
        if self._api is None or self._kitchen_name is None:
            print 'DKActiveServingWatcher: start_making_watcher failed requires api and kitchen name'
            return False
        try:
            self.run_thread = Thread(target=make_watcher_thread, args=(self, 1), name='DKActiveServingWatcher')
            self.run_thread.start()
        except Exception, e:
            print 'DKActiveServingWatcher: start_making_watcher exception %s' % e
            return False
        return True

    def wait_until_watcher_complete(self):
        try:
            self.run_thread.join()
        except Exception, e:
            print 'DKActiveServingWatcher: wait_until_watcher_complete exception %s' % e
            return False

    def watch(self):
        cache = DKActiveServingCache().get_cache()
        print 'watching ...'
        rc = self._api.orderrun_detail(self._kitchen_name, {'summary': True})
        if rc.ok() and rc.get_payload() is not None:
            payload = rc.get_payload()
            for serving in payload:
                if isinstance(serving, dict) is True and 'summary' in serving:
                    if 'current' not in cache:
                        cache['current'] = serving['summary']
                    else:
                        cache['previous'] = cache['current']
                        cache['current'] = serving['summary']
                        DKActiveServingWatcher._print_changes(cache, False)

    @staticmethod
    def print_serving_summary(serving):
        temp_cache = dict()
        temp_cache['current'] = serving
        temp_cache['previous'] = serving
        DKActiveServingWatcher._print_changes(temp_cache, True)

    @staticmethod
    def _print_changes(cache, trace=False):
        found_change = False
        # print top level changes
        if 'current' in cache and 'previous' in cache:
            found_change = DKActiveServingWatcher._print_serving_summary(cache, trace)
        if found_change is False:
            stdout.write(' . \r')
            stdout.flush()
        return found_change

    @staticmethod
    def _print_serving_summary(cache, trace=False):
        cur = cache['current']
        pre = cache['previous']
        nodes = list()
        found_change = False
        for item, val in cur.iteritems():
            if isinstance(val, dict):
                nodes.append(item)
            else:
                if cur[item] != pre[item] and item != 'hid':
                    print '%s(%s..) %s:  %s' % (cur['name'], cur['hid'][:5], item, val)
                    found_change = True
                else:
                    if trace is True:
                        print 'Trace: %s(%s..) %s:  %s' % (cur['name'], cur['hid'][:5], item, val)
        for node_name in nodes:
            if DKActiveServingWatcher._print_node_changes(cur['name'], cur['hid'][:5], cur[node_name], pre[node_name],
                                                          node_name, trace) is True:
                found_change = True

        return found_change

    # node_name,
    #   data_source/data_sink/actions
    #       file_name
    #           keys
    #               key_name
    #                   status
    #           tests
    #               applies-to-keys
    #               results
    #               status
    #           status
    #           timing
    #           type
    #   status
    #   timing
    #   type
    @staticmethod
    def _print_node_changes(rname, hid, cur, pre, item_print_string, trace=False):
        found_change = False
        if isinstance(cur, dict) and isinstance(pre, dict):
            for item, val in cur.iteritems():
                new_item_print_string = '%s: %s' % (item_print_string, item)
                if isinstance(val, dict):
                    if DKActiveServingWatcher._print_node_changes(rname, hid, cur[item], pre[item],
                                                                  new_item_print_string, trace) is True:
                        found_change = True
                else:
                    if cur[item] != pre[item]:
                        print '%s(%s..) %s: %s:  %s' % (rname, hid, item_print_string, item, cur[item])
                        found_change = True
                    else:
                        if trace is True:
                            print 'Trace: %s(%s..) %s: %s:  %s' % (rname, hid, item_print_string, item, cur[item])
        else:
            print 'cur and pre fucked up (%s) (%s)' % (cur, pre)
        return found_change


class DKActiveServingCache(object):
    __shared_state = {}
    _cache = dict()
    _time = 'last-update-time'

    def __init__(self):
        self.__dict__ = self.__shared_state

    def __repr__(self):
        return self.__shared_state

    def __str__(self):
        return self.__repr__()

    def get_cache(self):
        return self._cache
