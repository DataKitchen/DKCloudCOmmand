from DKCloudAPI import DKCloudAPI
__author__ = 'DataKitchen, Inc.'

from DKReturnCode import DKReturnCode
import pickle

class DKCloudAPIMock(DKCloudAPI):

    def __init__(self, dk_cli_config):
        DKCloudAPI.__init__(self, dk_cli_config)
        self._load()

    def _load(self):
        self._pickles = {}

        pickle_from_disk = pickle.load(open("files/merge_kitchens_improved_success.p", "rb"))
        self._pickles['merge_success'] = pickle_from_disk

        pickle_from_disk = pickle.load(open("files/merge_kitchens_improved_conflicts.p", "rb"))
        self._pickles['merge_conflicts'] = pickle_from_disk
        self._pickles['child_ut_6d887fc6'] = pickle_from_disk
        self._pickles['merge-child_ut_6d887fc6'] = pickle_from_disk

    def _get_token(self, unit_test=False):
        return 'mock-token'

    def list_kitchen(self):
        class MockResponse():
            text ="{\"kitchens\": [{\"recipeoverrides\": [{\"variable\": \"var-name\", \"category\": \"category-name\", \"value\": \"var-value\"}], \"kitchen-staff\": [\"dk-test\", \"dk-test2\", \"username2\"], \"name\": \"base-test-kitchen\", \"kept on delete\": \"changes in code and selected serving information .... recipebook ... more servinginfo\", \"recipes\": [\"recipename1\", \"recipename2\"], \"DKDOC3\": \"there is only one kitchen.json in doc in per customer (e.g DKcustomer/dk) git branch template directory\", \"DKDOC2\": \" this doc in git branch, that is where we get the branch-name\", \"DKDOC\": \"recipebooks give servings, they the same name as the kitchens; recipes + branch give chefs\", \"parent-kitchen-sha\": \"35cd4cfedd947eb1eaff9de51febcbcf0c6b178f\", \"parent-kitchen\": \"master\", \"agile-process\": {\"project\": \"project-name\", \"wiki\": \"wiki-name\", \"current-sprint\": \"sprint-name\"}, \"description\": \"example description\"}, {\"recipeoverrides\": [{\"variable\": \"var-name\", \"category\": \"category-name\", \"value\": \"var-value\"}], \"kitchen-staff\": [\"dk-test\", \"dk-test2\", \"username2\"], \"name\": \"kitchens-plus\", \"kept on delete\": \"changes in code and selected serving information .... recipebook ... more servinginfo\", \"recipes\": [\"recipename1\", \"recipename2\"], \"DKDOC3\": \"there is only one kitchen.json in doc in per customer (e.g DKcustomer/dk) git branch template directory\", \"DKDOC2\": \" this doc in git branch, that is where we get the branch-name\", \"DKDOC\": \"recipebooks give servings, they the same name as the kitchens; recipes + branch give chefs\", \"parent-kitchen-sha\": \"24ebbb9dbf729500f0f4f7fbb83b95b4ebc1369d\", \"parent-kitchen\": \"master\", \"agile-process\": {\"project\": \"project-name\", \"wiki\": \"wiki-name\", \"current-sprint\": \"sprint-name\"}, \"description\": \"example description 2016-01-30 16:01:13.734790\"}, {\"recipeoverrides\": [{\"variable\": \"var-name\", \"category\": \"category-name\", \"value\": \"var-value\"}], \"kitchen-staff\": [\"dk-test\", \"dk-test2\", \"username2\"], \"name\": \"master\", \"kept on delete\": \"changes in code and selected serving information .... recipebook ... more servinginfo\", \"recipes\": [\"recipename1\", \"recipename2\"], \"DKDOC3\": \"there is only one kitchen.json in doc in per customer (e.g DKcustomer/dk) git branch template directory\", \"DKDOC2\": \" this doc in git branch, that is where we get the branch-name\", \"DKDOC\": \"recipebooks give servings, they the same name as the kitchens; recipes + branch give chefs\", \"parent-kitchen-sha\": \"24ebbb9dbf729500f0f4f7fbb83b95b4ebc1369d\", \"parent-kitchen\": \"master\", \"agile-process\": {\"project\": \"project-name\", \"wiki\": \"wiki-name\", \"current-sprint\": \"sprint-name\"}, \"description\": \"example description\"}]}"
            def __init__(self):
                pass
        return self._get_json(MockResponse)['kitchens']

    def merge_kitchens_improved(self, from_kitchen, to_kitchen, resolved_conflicts=None):
        return self._pickles[from_kitchen]

    def delete_orderrun(self, orderrun_id):
        """
        :param self: self
        :param orderrun_id: string ; 'good' return a good value ; 'bad' return a bad value
        :rtype: DKReturnCode
        """
        rc = DKReturnCode()
        if orderrun_id == 'good':
            rc.set(rc.DK_SUCCESS, None, None)
        else:
            rc.set(rc.DK_FAIL, 'ServingDeleteV2: unable to delete OrderRun')
        return rc

    def update_kitchen(self, update_kitchen, message):
        return True

    def create_kitchen(self, existing_kitchen_name, new_kitchen_name, message):
        return True

    def delete_kitchen(self, existing_kitchen_name, message):
        return True
