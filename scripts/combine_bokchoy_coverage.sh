#!/bin/bash


dst_path=$HOME/results/$TDDIUM_SESSION_ID/session/bokchoy_coverage_combined.html
xmls_path=$HOME/results/$TDDIUM_SESSION_ID/session/bok_choy

ls -R $xmls_path

echo 'Combining Bok-Choy Coverage...'

diff-cover $xmls_path/*.xml --compare-branch=origin/master --html-report $dst_path
