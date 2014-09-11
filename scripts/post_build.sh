current_path=`pwd`

echo $current_path


reports_path=$current_path/reports

tree $reports_path

echo $reports_path

dest_path=$HOME/results/$TDDIUM_SESSION_ID/session/

echo $dest_path


pep8_rpt=$reports_path/diff_quality/diff_quality_pep8.html
pylint_rpt=$reports_path/diff_quality/diff_quality_pylint.html

cp -f $pep8_rpt $dest_path
cp -f $pylint_rpt $dest_path
