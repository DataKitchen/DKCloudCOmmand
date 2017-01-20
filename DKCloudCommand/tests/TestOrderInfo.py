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

    def test_it(self):
        orderrun_detail = pickle.load(open("files/orderrun_detail.p", "rb"))

        print orderrun_detail

        pass





if __name__ == '__main__':
    unittest.main()
