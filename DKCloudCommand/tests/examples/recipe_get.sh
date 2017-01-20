#!/usr/bin/env bash

rm -rf kitchens_remote
mkdir -p kitchens_remote
cd kitchens_remote

kitchen_name="recipe_get_test"
rm -rf ${kitchen_name}
dk kitchen-delete ${kitchen_name}
dk kitchen-create --parent CLI-Top ${kitchen_name}
dk kitchen-get --recipe simple ${kitchen_name}
cd ${kitchen_name}/simple
echo -e "lineZ\n" > modified_file_on_remote.txt
dk file-create modified_file_on_remote.txt -m "modified_file_on_remote"

echo -e "line??\n" > deleted_file_on_remote.txt
dk file-create deleted_file_on_remote.txt -m "deleted_file_on_remote"

cd ../../..
rm -rf kitchens_local
mkdir -p kitchens_local
cd kitchens_local
rm -rf ${kitchen_name}
dk kitchen-get --recipe simple ${kitchen_name}


cd ../kitchens_remote/${kitchen_name}/simple
echo -e "lineZ\nlineY\n" > modified_file_on_remote.txt
dk file-update modified_file_on_remote.txt -m "modified_file_on_remote added new line"

echo -e "line99\n" > new_file_on_remote.txt
dk file-create new_file_on_remote.txt -m "new_file_on_remote"

rm deleted_file_on_remote.txt
dk file-delete -m "deleted_file_on_remote" deleted_file_on_remote.txt


cd ../../../kitchens_local/${kitchen_name}/simple

dk recipe-status

dk recipe-get








