#!/bin/bash
 

current_path=`pwd`
bok_choy_reports_path=$current_path/reports/bok_choy
bok_choy_cov_xml=$bok_choy_reports_path/acceptance_coverage.xml
dest_path=$HOME/results/$TDDIUM_SESSION_ID/session/bok_choy

mkdir -p $dest_path

 
case $1 in
   "shard1")	
	echo "Collecting Coverage for Bok-Choy Shard1"
	paver bokchoy_coverage 
	echo "Merging Coverage into a Single HTML File for Bok-Choy Shard1"
	python ./scripts/cov_merge.py bok_choy bok_choy_shard1_coverage.html	
	cp -f $bok_choy_cov_xml $dest_path/acceptance_coverage1.xml
	;;
   "shard2")
	echo "Collecting Coverage for Bok-Choy Shard2"
	paver bokchoy_coverage 
	echo "Merging Coverage into a Single HTML File for Bok-Choy Shard2"
	python ./scripts/cov_merge.py bok_choy bok_choy_shard2_coverage.html
	cp -f $bok_choy_cov_xml $dest_path/acceptance_coverage2.xml
	;;
   "shard3")
	echo "Collecting Coverage for Bok-Choy Shard3"
	paver bokchoy_coverage 
	echo "Merging Coverage into a Single HTML File for Bok-Choy Shard3"
	python ./scripts/cov_merge.py bok_choy bok_choy_shard3_coverage.html
	cp -f $bok_choy_cov_xml $dest_path/acceptance_coverage3.xml
	;;
   *)
	echo "Invalid Bok-Choy Shard Value!";;
esac
