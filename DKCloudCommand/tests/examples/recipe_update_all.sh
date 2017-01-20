#!/usr/bin/env bash

mkdir -p kitchens
cd kitchens

recipe_name="recipe_update_all_test"
rm -rf ${recipe_name}
dk kitchen-delete ${recipe_name}

dk kitchen-create --parent CLI-Top ${recipe_name}
dk kitchen-get --recipe simple ${recipe_name}

cd ${recipe_name}
cd simple
echo "line1\n" > new_file.txt
echo "lineA\n" > deleted_file.txt
echo "lineZ\n" > modified_file.txt

echo "line1\n" > new_file2.txt
echo "lineA\n" > deleted_file2.txt
echo "lineZ\n" > modified_file2.txt

# dk file-create new_file.txt -m "test file"
dk file-add deleted_file.txt -m "test file"
dk file-add modified_file.txt -m "test file"
dk file-add deleted_file2.txt -m "test file"
dk file-add modified_file2.txt -m "test file"

rm deleted_file.txt
rm deleted_file2.txt
rm -rf node2

echo "line99\n" > modified_file.txt
echo "line99\n" > modified_file2.txt
dk recipe-status

dk recipe-update --dryrun -m ""

# dk recipe-update -m ""







