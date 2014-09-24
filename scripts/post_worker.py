import tarfile
import os
import shutil


def copy_bokchoy_coverage_data(source_path, files):
    """Copy coverage data `files` present in `source_path` to solano results directory"""
    destination_path = os.path.join(session_path, 'bok_choy')

    if not os.path.exists(destination_path):
        print 'Creating {}'.format(destination_path)
        os.makedirs(destination_path)

    for f in files:
        if f.startswith('.coverage.'):
            src_file = os.path.join(source_path, f)
            dst_file = os.path.join(destination_path, f)
            print 'Copying {src} to {dst}'.format(src=src_file, dst=dst_file)
            shutil.copyfile(src_file, dst_file)


full_path = os.path.realpath(__file__)
source_dir = full_path.replace("scripts/post_worker.py", "reports/")
output_filename = full_path.replace("post_worker.py", "reports.tar.gz")

session_path = os.path.join(
    os.environ['HOME'],
    'results',
    os.environ['TDDIUM_SESSION_ID'],
    'session')

print "source dir:", source_dir

count = 0

# walk through every subdirectory & add the folder if it is not empty
with tarfile.open(output_filename, "w:gz") as tar:
    for (path, dirs, files) in os.walk(source_dir):
        if len(files) > 0:
            print "tarring:", path
            
            # copy bok-choy .coverage.* files for combining later
	    if os.path.basename(path) == 'bok_choy':
                copy_bokchoy_coverage_data(path, files)
                
            tar.add(path, arcname=os.path.basename(path))
            count += 1

tar.close()

file_dest = os.path.join(session_path, 'reports.tar.gz')

# if the tar file is not empty, copy it to the proper place
if count > 0:
    print 'copying tar file to:', file_dest
    shutil.copyfile(output_filename, file_dest)

# finding if there is any screenshot or log file
print 'attaching failed screenshots and logs (if any)'
for (path, dirs, files) in os.walk('test_root/log'):
    for filename in files:
        if filename.find('png') != -1 or filename.find('log') != -1:
            filepath = os.path.join(path, filename)
            print 'copying file:', filepath
            destpath = os.path.join(session_path, filename)
            print 'destination:', destpath
            shutil.copyfile(filepath, destpath)

print 'TDDIUM_SESSION_ID:', os.environ['TDDIUM_SESSION_ID']
