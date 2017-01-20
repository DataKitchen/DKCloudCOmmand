#!/usr/bin/env bash

mkdir -p kitchens
cd kitchens

rm -rf child-delete-me
rm -rf parent-delete-me
dk kitchen-delete child-delete-me
dk kitchen-delete parent-delete-me

dk kitchen-create --parent CLI-Top parent-delete-me
dk kitchen-get --recipe simple parent-delete-me

dk kitchen-create --parent parent-delete-me child-delete-me
dk kitchen-get --recipe simple child-delete-me

cd parent-delete-me
cd simple
echo "line1\n" > file01.txt
echo "lineA\nlineC" > file02.txt
dk file-create file01.txt -m "test file"
dk file-create file02.txt -m "test file"
cd ../..
cd child-delete-me
cd simple
echo "line1\nline2" > file01.txt
echo "lineA" > file02.txt
dk file-create file01.txt -m "test file"
dk file-create file02.txt -m "test file"

# Returns with 5 changes across 3 files
# Conflicts have been written to the files between the >>>> and <<<< conflict tags.
echo "dk kitchen-merge -s child-delete-me -t parent-delete-me"
dk kitchen-merge -s child-delete-me -t parent-delete-me

# Try again and it will show you that you have unresolved conflicts
echo "dk kitchen-merge -s child-delete-me -t parent-delete-me"
dk kitchen-merge -s child-delete-me -t parent-delete-me

# Show the merge conflicts
echo "dk recipe-conflicts"
dk recipe-conflicts

# Resolve the conflicts. Normally you would edit the files to resolve them.
echo "dk file-resolve file01.txt"
dk file-resolve file01.txt
echo "dk file-resolve file02.txt"
dk file-resolve file02.txt

# With all the conflicts resolved, you can now merge.
echo "dk kitchen-merge -s child-delete-me -t parent-delete-me"
dk kitchen-merge -s child-delete-me -t parent-delete-me

# Returns nothing to do.
# dk kitchen-merge -s parent-delete-me -t child-delete-me




