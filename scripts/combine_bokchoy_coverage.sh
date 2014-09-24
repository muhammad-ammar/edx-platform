#!/bin/bash

root_path=`pwd`

echo "Root path is "$root_path

cov_path=$HOME/results/$TDDIUM_SESSION_ID/session

echo "Session path is "$HOME/results/$TDDIUM_SESSION_ID/session/
ls -aR $HOME/results/$TDDIUM_SESSION_ID/session/

ls -R $cov_path

cat >$cov_path/.coveragerc <<EOL
[run]
data_file = .coverage
source = lms, cms, common/djangoapps, common/lib
omit = lms/envs/*, cms/envs/*, common/djangoapps/terrain/*, common/djangoapps/*/migrations/*, */test*, */management/*, */urls*, */wsgi*
parallel = True

[paths]
source =
    $root_path
    /mnt/home/*/src/repo/edx-platform

[report]
ignore_errors = True

[html]
title = Bok Choy Test Coverage Report
directory = reports/bok_choy/cover
EOL


echo 'Combining Bok-Choy Coverage...'

cd $cov_path

coverage combine --rcfile=.coveragerc
coverage html --rcfile=.coveragerc

ls -R $cov_path

cd $root_path

python ./scripts/cov_merge.py bok_choy $cov_path/reports

rm -f $cov_path/.coverage*

