import codecs
import os
import re
from itertools import chain
from operator import itemgetter

import nltk
import numpy as np
import pandas as pd
from lxml import etree
from unidecode import unidecode

from CVCodingTool.src.section_parser import EduParser, PubParser, GrantParser


class CVParser:
    def __init__(self, filepath, filename):
        """
        This function initializes the file structure, based on the given filename, filepath and
        header list.

        The procedure is:
        file_preprocess: PDF file --> XML file parsed tree
        getroot: XML file parsed tree --> XML file parsed root
        text_preprocess: XML file parsed root --> Preprocessed Texts
        nltk.Index: Preprocessed Texts --> Grouped fonts
        get_partition: Preprocessed Texts and Grouped fonts --> File partition structure

        It also provides API for getting partition text of a particular partition: get_partition_contents

        :param filepath:
        :param filename:
        """
        self.filepath = filepath
        self.filename = filename
        self.header_list = r'education|publication|fellowship|reference|presentation|profession|' \
                           r'languages|experience|position|research|conference|service|journal|' \
                           r'peer|award|activity|activities|review|skill|academic|article|paper|grant|' \
                           r'training|bibliography|book|lecture'

        try:
            self.tree = self.file_preprocess()
            self.texts = self.text_preprocess()
            self.width_groups = nltk.Index((text.get('width'), text.text) for text in self.texts)
            self.font_groups = nltk.Index((text.get('font'), text.text) for text in self.texts
                                          if text.text
                                          # if int(text.get('width')) < 420 or len(re.split(r'\s+', text.text)) <= 3
                                          if len(text.text) < 100
                                          if not re.findall(r"[#*()$]", text.text))
            self.left_groups = nltk.Index((text.get('left'), text.text) for text in self.texts
                                          if text.text
                                          if len(text.text) < 100
                                          if not re.findall(r"[#*()$]", text.text))
            self.height_groups = nltk.Index((text.get('height'), text.text) for text in self.texts
                                            if text.text
                                            if len(text.text) < 100
                                            if not re.findall(r"[#*()$]", text.text))
            self.partition = self.get_partition()
        except:
            self.partition = None

    def file_preprocess(self):
        """
        Do some file preprocessing. This includes transform pdf to xml, remove <b> and
        <i> and other special tokens, remove unnecessary files.

        :return: Parsed xml tree.
        """
        file_pdf = os.path.join(self.filepath, self.filename)
        os.system('pdftohtml -xml %s >& /dev/null' % file_pdf)
        file_xml = re.sub(r'(.*)(?:\.pdf)$', r'\1.xml', file_pdf)
        os.system("sed -ie 's/\xa0//g;s/\&amp\;//g;' %s >& /dev/null" % file_xml)
        os.system('rm -rf %s/*.{png,jpg}' % self.filepath)
        parser = etree.XMLParser(ns_clean=True, recover=True)

        try:
            tree = etree.parse(codecs.open(file_xml, encoding='utf-8'), parser=parser)
        except:
            tree = etree.parse(codecs.open(file_xml, encoding='ISO-8859-1'), parser=parser)

        etree.strip_tags(tree, *['b', 'i', 'a'])
        os.system('rm -rf %s/*.{xmle,xml}' % self.filepath)
        return tree

    def text_preprocess(self):
        """
        Text Preprocessing is very important:
        STEP I: Extract only text that is not None if spaces and dots are removed.
        STEP II: Remove all spaces in the beginning and the end, also if more than ten underscores,
                 remove it, and change the width to 100. (It is because such many underscores may
                 be headers, so remove it and set width can match subsequent criterion).
        STEP III: Three scenarios:
                  Scenario I: Both belong to the same line. They are merged iff they are headers.
                              Inside merging, if it is 'E' merges with 'ducation', no space is
                              added, otherwise add a space. If they are not both headers, although
                              they belong to the same line, ignore them.
                  Scenario II: The previous one and the pre-previous one belong to the same line.
                               Merge the texts and set pre_pos.
                  Scenario III: Normal case. Set pre_pos.
        STEP IV: remove extra spaces.

        :return: Preprocessed Text.
        """
        if not self.tree:
            return None
        # STEP I
        texts_initial = [text for text in self.tree.getroot().xpath('.//text | .//page')
                         if text.text if re.sub(r'[ .]+', '', text.text) != '']
        texts_list = []
        for text in texts_initial:
            if text.get('top') == '0':
                texts_list.append([])
            else:
                texts_list[-1].append(text)
        texts_list = [sorted(i, key=lambda x: int(x.get('top'))) for i in texts_list]

        # STEP II
        for texts in texts_list:
            pre_pos = 0
            for pos, text in enumerate(texts[1:]):
                if text.get('top') == '0':
                    continue
                pos += 1
                top_diff = int(texts[pos].get('top')) - int(texts[pre_pos].get('top'))
                texts[pos].text = text.text.strip()
                if re.findall(r'_{10,}', text.text):
                    texts[pos].text = re.sub(r'[_]', '', text.text)
                    texts[pos].set('width', '100')
                if re.findall(r'(?:[A-Za-z] ){4,}', text.text):
                    texts[pos].set('width', '1')
                # STEP III
                if -15 < int(texts[pos].get('top')) - int(texts[pre_pos].get('top')) < 12:
                    if abs(int(texts[pos - 1].get('left')) - int(text.get('left'))) < 120:
                        if texts[pos - 1].get('width') == '-1' or texts[pos - 1].get('width') == '0':
                            texts[pre_pos].text += text.text
                            text.set('width', '-1')
                            texts[pos].text = ''
                        elif not self.header_checker(texts[pre_pos].text) and not self.header_checker(text.text):
                            texts[pre_pos].text += ' ' + text.text
                            texts[pos].text = ''
                        else:
                            pre_pos = pos
                    else:
                        pre_pos = pos
                elif -600 <= top_diff <= -15:
                    texts[pre_pos - 1].text += ' ' + texts[pre_pos].text
                    texts[pre_pos].text = ''
                    pre_pos = pos
                else:
                    if len(text.text) == 1 and text.text.isupper():
                        text.set('width', '0')
                        pre_pos = pos
                    elif abs(int(texts[pre_pos].get('left')) - int(text.get('left'))) < 3 \
                            and len(re.split('\s+', text.text)) <= 3 \
                            and int(texts[pre_pos].get('left')) <= 80 \
                            and len(re.split('\s+', texts[pre_pos].text)) <= 3 \
                            and re.sub(r'\W+', '', texts[pre_pos].text) != '' \
                            and texts[pre_pos].get('font') == text.get('font') \
                            and abs(int(texts[pre_pos].get('top')) - int(text.get('top'))) < 150:
                        texts[pre_pos].text += ' ' + text.text
                        texts[pos].text = ''
                    else:
                        pre_pos = pos

        # STEP IV
        for pos, texts in enumerate(texts_list):
            for text in texts:
                text.text = re.sub(r'\s{2,}', r' ', text.text)
                text.text = unidecode(text.text)
            texts_list[pos] = [text for text in texts if text.text != '']

        return list(chain.from_iterable(texts_list))

    def refine_extractor(self, attr_group, attr, refine_function, threshold, findall_exp, ratio=False):
        """
        This function defines a general interface refinement function.
        It will first see whether we need a ratio at last, and do corresponding actions.
        Then get the maximum value, and compare to the threshold (The threshold is empirical
        figure by my own estimation based on accuracy rate). If passed, then get the result
        header name along with its position in Texts.

        Two checkers will work here. First one is the validity checker, to check whether it
        is indeed the header list. Second one is the special part checker, by using this
        I mean to check for some special header (current only education is included). If this
        one is not found in the current header list, it will be added.

        :param attr_group: The attribute group used, for example, font_group
        :param attr: The attribute group used, for example, font. Should be consistent with attr_group
        :param refine_function: A function that must return True or False to check whether it
                                should be a header
        :param threshold: A value that compared with the maximum value got from the refined list.
        :param findall_exp: If passed threshold check, use this function to extract header text.
                            It usually removes many invalid tokens. (I also remove spaces in
                            the sake of extra spaces).
        :param ratio: A flag indicating whether it is a ratio or not.
        :return: if get all the checkers passed, return a list with positions and names; if not,
                 return None.
        """

        if ratio:
            criterion = dict((key, np.sum([refine_function(re.sub(r' ', '', va)) for va in val]) / len(val))
                             for key, val in attr_group.items()
                             if isinstance(val, list) if len(val) >= 5)
        else:
            criterion = dict((key, np.sum([refine_function(re.sub(r' ', '', va)) for va in val]))
                             for key, val in attr_group.items()
                             if isinstance(val, list) if len(val) >= 5)

        if not criterion:
            return None

        criterion_max = max(criterion.values())
        if len([val for val in criterion.values() if val == criterion_max]) > 1:
            return None

        if criterion_max > threshold:
            criterion_max_index = max(criterion.items(), key=itemgetter(1))[0]
            result = [(pos, ''.join(re.findall(findall_exp, val))) for pos, val in
                      [(pos, text.text) for pos, text in enumerate(self.texts)
                       if text.get(attr) == criterion_max_index]
                      if refine_function(val)]

            if not result or len(result) >= 20:
                return None

            # Double check: First check validity, second check special group (Current only education)
            if np.sum(self.header_checker(header) for _, header in result) / len(result) > 0.3:
                for string in ['education', 'publication|bibliography']:
                    if not re.findall(string, ''.join(val for pos, val in result), re.IGNORECASE):
                        special_group = self.refine_special_treatment(string)
                        if special_group:
                            result = list(sorted(set(result + special_group), key=itemgetter(0)))
                return [(pos, re.sub(r' ', '', val)) for pos, val in result]

        return None

    def refine_special_treatment(self, string):
        """
        This function is just used for find a specific string and return the font group that
        contains it.

        :param string: special treatment string.
        :return: If found this string in the Text, return the corresponding font group; else
                 return None.
        """
        special_token = [(pos, ''.join(re.findall(r'[A-Za-z*,()\-&]+', text.text)))
                         for pos, text in enumerate(self.texts)
                         if re.findall(r'^%s|%s\s+\(.+\)' % (string, string), text.text, re.IGNORECASE)
                         if self.header_checker(text.text)]
        return special_token or None

    def header_checker(self, header):
        """
        Checker whether the string should be a header. Use a manually-maintained header list.

        :param header: a string tentative to be a header.
        :return: boolean indicating whether it is a header.
        """
        if re.findall(r'(?:[A-Za-z] ){4,}', header):
            header = re.sub(r' ', '', header)
        if re.findall(self.header_list, re.sub(r' ', '', header), re.IGNORECASE) \
                and len(re.split(r'\s+', header)) <= 8 \
                and len(re.findall(r"^[A-Z]", header)) > 0:
            return True
        else:
            return False

    def get_partition(self):
        """
        This function calls the general refine_extractor in three formats:
        1. Check capitalized letters number.
        2. Check capitalized letters ratio.
        3. Check header checker letters ratio.

        The early call has privileges beyond the latter call, so if early one can return result,
        it will be count as the final result. If None is return after all calls, font group is
        returned.

        :return: Header list along with its positions in Texts.
        """

        capitalize_paras = {"attr_group": self.font_groups,
                            "attr": 'font',
                            "refine_function": lambda x: x.isupper() and len(re.split('\s+', x)) <= 8,
                            "threshold": 5,
                            "findall_exp": r'[A-Z\*,\-\(\)&]+'}
        capitalize_ratio_paras = {"attr_group": self.font_groups,
                                  "attr": 'font',
                                  "refine_function": lambda x: x.isupper() and len(re.split('\s+', x)) <= 8,
                                  "threshold": 0.3,
                                  "findall_exp": r'[A-Z\*,\-\(\)&]+',
                                  "ratio": True}
        font_ratio_paras = {"attr_group": self.font_groups,
                            "attr": 'font',
                            "refine_function": self.header_checker,
                            "threshold": 0.2,
                            "findall_exp": r'[A-Za-z\*,\-\(\)&]+',
                            "ratio": True}
        left_ratio_paras = {"attr_group": self.left_groups,
                            "attr": 'left',
                            "refine_function": self.header_checker,
                            "threshold": 0.25,
                            "findall_exp": r'[A-Za-z\*,\-\(\)&]+',
                            "ratio": True}
        height_ratio_paras = {"attr_group": self.height_groups,
                              "attr": 'height',
                              "refine_function": self.header_checker,
                              "threshold": 0.25,
                              "findall_exp": r'[A-Za-z\*,\-\(\)&]+',
                              "ratio": True}

        special_width = ['0']
        for width in special_width:
            if self.width_groups[width] and 20 >= len(self.width_groups[width]) >= 4 \
                    and np.sum([self.header_checker(val) for val
                                in self.width_groups[width]]) / len(self.width_groups[width]) > 0.5:
                return [(pos, re.sub(r'\s', '', val.text)) for pos, val in enumerate(self.texts)
                        if val.get('width') == width]

        partition_refine_methods = [capitalize_paras, capitalize_ratio_paras, font_ratio_paras,
                                    left_ratio_paras, height_ratio_paras]
        for val in partition_refine_methods:
            val_partition = self.refine_extractor(**val)
            if val_partition:
                return val_partition

        return None

        # raise Exception("This file cannot be parsed. Please Check the file format.")

    def get_partition_texts(self, partition_name):
        """
        Based on the header list for this particular CV, it will extract a partition
        part.

        :param partition_name: The partition name you are looking for.
        :return: Partition Texts.
        """
        if not self.partition:
            return None

        contents = []
        target_partitions = [(i, pos) for i, (pos, val) in enumerate(self.partition)
                             if re.findall(partition_name, val, re.IGNORECASE)]
        if target_partitions:
            for part in target_partitions:
                begin_index = part[1] + 1
                if part[0] == len(self.partition) - 1:
                    end_index = len(self.texts)
                else:
                    end_index = self.partition[part[0] + 1][0]
                contents += self.texts[begin_index:end_index]
            return contents
        else:
            return None

    def get_partition_contents(self, partition_obj):
        partition_map = {"education": EduParser,
                         "publication": PubParser,
                         "grant": GrantParser}
        partition = partition_obj['name']
        partition_str = re.split(r'\|', partition_obj['string'])
        partition_parser = partition_map.get(partition)
        partition_header = re.split(r',', partition_obj['header'])

        partition_texts = [self.get_partition_texts(val) for val in partition_str]
        # For test only!!!
        # TODO: Need to add file_type flag
        # self.file_type = 'Publication'
        # if self.file_type == 'Publication':
        #     partition_texts = [self.texts]

        if partition in partition_map.keys():
            partition_paras = {"texts": partition_texts,
                               "filename": self.filename,
                               "header": partition_header}
            partition_dict = partition_parser(**partition_paras).section_dict
            partition_df = pd.DataFrame.from_dict(partition_dict)

            return partition_df.drop_duplicates()
        else:
            raise Exception("No API for partition. %s" % partition)
