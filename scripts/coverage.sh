#!/bin/bash

current_path=`pwd`
bok_choy_reports_path=$current_path/reports/bok_choy
bok_choy_cov_data=$bok_choy_reports_path/.coverage
dest_path=$HOME/results/$TDDIUM_SESSION_ID/session/bok_choy

mkdir -p $dest_path 

echo '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
ls -aR $bok_choy_reports_path
echo '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'

case $1 in
   "shard1")	
	echo "Copying Bok-Choy Shard1 Coverage Data to "$dest_path
	cp -f $bok_choy_cov_data $dest_path/.coverage.1
	;;
   "shard2")
	echo "Copying Bok-Choy Shard2 Coverage Data to "$dest_path
	cp -f $bok_choy_cov_data $dest_path/.coverage.2
	;;
   "shard3")
	echo "Copying Bok-Choy Shard3 Coverage Data to "$dest_path
	cp -f $bok_choy_cov_data $dest_path/.coverage.3
	;;
   *)
	echo "Invalid Bok-Choy Shard Value!";;
esac
