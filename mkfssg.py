#!/usr/bin/env python3
from jinja2 import Environment, FileSystemLoader #, meta
import os
from sys import stderr
from collections import defaultdict
import toml
global config
while True:
    try:
        with open('_mkfssg.toml', 'r') as f:
            config = toml.load(f)
            break
    except FileNotFoundError:
        os.chdir("..")
env = Environment(loader=FileSystemLoader(config["templ_dir"]))
static_dir = config["static_dir"]
target_dir = config["target_dir"]
def files(root_dir):
    files = set()
    dirs = set()
    for dir_path, dirnames, filenames in os.walk(root_dir):
        files.update({(
            os.path.relpath(dir_path, root_dir),
            file
            ) for file in filenames})
        dirs.update({(
            os.path.relpath(dir_path, root_dir),
            dir
            ) for dir in dirnames})
    return files, dirs
def dir_dict(files, dirs):
    res = {'.': set()}
    for d, dir in dirs:
        res[os.path.join(d, dir)] = set()
    for d, file in files:
        res[d].add(file)
    return res
static_files, static_subdirs = files(static_dir)
static_dir_dict = dir_dict(static_files, static_subdirs)
target_files, target_subdirs = files(target_dir)
target_dir_dict = dir_dict(target_files, target_subdirs)
t_dsts = {i['dst'] for i in config["templ"]}
t_dst_subdirs = defaultdict(set)
for i in t_dsts:
    d, b = os.path.split(i)
    d = os.path.relpath('.', d)
    t_dst_subdirs[d].add(b)
t_dst_subdirs.default_factory = None
class AtomicFile:
    def __init__(self, path):
        self.dir, self.name = os.path.split(path)
    def __enter__(self):
        self.file = os.open(self.dir, os.O_TMPFILE | os.O_WRONLY)
        return self.file.__enter__()
    def __exit__(self, *args, **kwargs):
        path = '/proc/self/fd/{0}'.format(self.file)
        os.link(path, self.name, src_dir_fd=0, follow_symlinks=True)
        return self.file.__exit__(*args, **kwargs)
planned_dirs = static_dir_dict | t_dst_subdirs.keys()
to_rmdir = target_subdirs - planned_dirs
to_mkdir = planned_dirs - target_subdirs
to_rm = target_files - (static_files | t_dsts)
while to_rm:
    for i in to_rm:
        try:
            os.unlink(os.path.join(target_dir, *i))
            to_rm.remove(i)
        except:
            pass
while to_rmdir:
    for i in to_rmdir:
        try:
            os.rmdir(os.path.join(target_dir, *i))
            to_rmdir.remove(i)
        except:
            pass
os.mkdir(target_dir)
for i in to_mkdir:
    os.makedirs(os.path.join(*i), exist_ok=True)
assert not static_files & t_dsts
for i in static_files:
    os.link(os.path.join(static_dir, *i),
            os.path.join(target_dir, *i))
for i in config['templ']:
    src = i["src"]
    dst = i["dst"]
    with AtomicFile(
            os.path.join(
                target_dir, dst)) as fh:
        fh.write(
            env.get_template(src).render())
exit(0)
