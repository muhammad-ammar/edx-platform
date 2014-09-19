#!/bin/bash

current_path=`pwd`
bok_choy_reports_path=$current_path/reports/bok_choy
bok_choy_cov_data=$bok_choy_reports_path/.coverage
dest_path=$HOME/results/$TDDIUM_SESSION_ID/session/bok_choy

mkdir -p $dest_path 

case $1 in
   "shard1")	
	echo "Copying Coverage Data Bok-Choy Shard1"
	cp -f $bok_choy_cov_data $dest_path/.coverage.1
	;;
   "shard2")
	echo "Copying Coverage Data Bok-Choy Shard2"
	cp -f $bok_choy_cov_data $dest_path/.coverage.2
	;;
   "shard3")
	echo "Copying Coverage Data Bok-Choy Shard3"
	cp -f $bok_choy_cov_data $dest_path/.coverage.3
	;;
   *)
	echo "Invalid Bok-Choy Shard Value!";;
esac
