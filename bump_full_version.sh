#!/bin/bash

NPM_UPDATE=$1

VERSION=$2

if [ $NPM_UPDATE == 1 ]; then
  cd src/api &&
  npm version --no-git-tag-version $VERSION &&
  cd - &&

  cd src/viewer &&
  npm version --no-git-tag-version $VERSION &&
  cd - &&

  cd src/packaged-viewer &&
  npm version --no-git-tag-version $VERSION &&
  cd -
fi

bump2version --allow-dirty $VERSION
