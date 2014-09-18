#!/bin/bash


dst_path=$HOME/results/$TDDIUM_SESSION_ID/session/bokchoy_coverage_combined.html
xmls_path=$HOME/results/$TDDIUM_SESSION_ID/session/bok_choy

diff-cover $xmls_path/*.xml --compare-branch=origin/master --html-report $dst_path
