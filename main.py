#!/usr/bin/env python
import argparse
import codecs
import json
import logging
import multiprocessing
import os
import re
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(".."))
from CVCodingTool.src.partition_parser import CVParser


class Manager:
    def __init__(self, config, partition, dev, directory):
        self.config = config
        self.partition = self.config[partition]
        self.directory = directory
        self.dev = self.config[dev]

    def run(self):
        dirs = self.directory or self.dev['dir']
        identifier = '%s_%s_%s' % (self.partition['name'], datetime.today().strftime('%Y%m%d%H%M%S'),
                                   os.path.split(dirs)[1])
        logging.basicConfig(format='%(message)s', filename='results/log/%s.log' % identifier, level=logging.DEBUG)
        if self.dev['destination'] == 'file':
            sys.stdout = codecs.open("results/parsed/%s.csv" % identifier, 'w+', "utf-8")

        print(self.partition['header'])

        for root, _, files in os.walk(dirs):
            if files:
                for file in files:
                    if re.search(r'^(?!\.).*(?:\.pdf)$', file):
                        self.writer(root, file)

        # Drop duplicates
        # table = pd.read_csv("results/parsed/%s.csv" % identifier)
        # table = table.drop_duplicates(subset='string_refined')
        # table.to_csv("results/parsed/%s.csv" % identifier, index=False)

    def writer(self, root, file):
        writer_kwargs = {"header": False, "index": False}
        try:
            sys.stdout.write(CVParser(root, file).get_partition_contents(self.partition).to_csv(**writer_kwargs))
        except Exception as e:
            logging.error('%s, %s' % (file, e))
            if not self.dev['fail_no_copy']:
                shutil.copyfile(os.path.join(root, file), os.path.join('results/failed', file))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='partition')
    parser.add_argument('-d', action='store', dest='dev')
    parser.add_argument('--dir', action='store', dest='directory')
    parser.add_argument('-r', action='store_true', dest='recursive')
    parser.set_defaults(recursive=False)
    parsed = parser.parse_args()

    with open('config.json', 'r') as f:
        config = json.load(f)


    def mp_runner(directory):
        Manager(config, parsed.partition, parsed.dev, directory).run()


    if parsed.recursive:
        for _, subdirs, _ in os.walk(parsed.directory):
            subdirs = [os.path.join(parsed.directory, val) for val in subdirs]
            pool = multiprocessing.Pool(10)
            pool.map(mp_runner, subdirs)
    else:
        mp_runner(parsed.directory)

# TODO: network rerun script
