import hashlib
import os
import re

import pandas as pd
import requests
from fuzzywuzzy import fuzz

from CVCodingTool.src.API import API_KEY_KIM
from CVCodingTool.src.environments import crossref_first_mapping, crossref_second_mapping, doi_mapping, \
    scopus_mapping, journal_mapping, author_mapping, grant_mapping
from CVCodingTool.src.tools import unicode_wrapper


class FieldParser:
    def __init__(self, dic, field_list, identifier):
        self.identifier = identifier
        self.dic = dic
        self.field_list = field_list
        self.record_dict = dict.fromkeys(self.field_list)
        self.record_dict.update(self.dic)
        self.transform_helper()

    def transform(self):
        return

    def transform_helper(self):
        if not self.dic.get(self.identifier):
            return
        self.transform()


class FieldNetworkParser(FieldParser):
    def __init__(self, dic, field_map, identifier, url, headers, response_code_id):
        self.url = url
        self.headers = headers
        self.resp = None
        self.response_code_id = response_code_id
        FieldParser.__init__(self, dic, list(field_map.keys()) + [response_code_id], identifier)

    def transform_helper(self):
        if not self.dic.get(self.identifier):
            return

        count = 0
        while True:
            try:
                self.resp = requests.get(self.url, headers=self.headers, timeout=20)
                self.record_dict[self.response_code_id] = self.resp.status_code
            except:
                self.record_dict[self.response_code_id] = 700

            if self.record_dict[self.response_code_id] == 700 and count < 5:
                count += 1
                continue
            elif self.record_dict[self.response_code_id] == 200:
                break
            else:
                return

        self.transform()


class TitleTransformer(FieldParser):
    def __init__(self, dic):
        FieldParser.__init__(self, dic, ['f_applicant_id', 'f_campus_id', 'f_first_name',
                                         'f_recruitment_id', 'f_last_name', 'f_year'], 'filename')

    def transform(self):
        campus_id, year, job_number, applicant_id, first_name, last_name = \
            re.split(r'_', os.path.splitext(self.record_dict['filename'])[0])
        new_dict = {'f_campus_id': campus_id, 'f_year': year, 'f_recruitment_id': job_number,
                    'f_applicant_id': applicant_id, 'f_first_name': first_name, 'f_last_name': last_name}
        self.record_dict.update(new_dict)


class EduFieldParser(FieldParser):
    def __init__(self, dic):
        FieldParser.__init__(self, dic, ['degree', 'year', 'institution'], 'string')

    def transform(self):
        result_mapping = {"degree": self.degree_parser,
                          "year": self.year_parser,
                          "institution": self.institution_parser}
        check_id = "degree"
        needed_id = ["year", "institution"]
        string = self.record_dict['string']
        val_dict = dict.fromkeys(result_mapping.keys())
        section_dict = []

        check_result = result_mapping[check_id](string)
        if check_result:
            for i in range(len(check_result)):
                for ke, func in result_mapping.items():
                    if not func(string):
                        val_dict[ke] = None
                    else:
                        if len(func(string)) >= len(check_result):
                            val_dict[ke] = func(string)[i]
                        else:
                            val_dict[ke] = func(string)[0]
                if any([val_dict[idx] for idx in needed_id]):
                    section_dict.append(val_dict.copy())
        self.record_dict = [{**self.record_dict, **val} for val in section_dict]

    @staticmethod
    def degree_parser(string):
        if re.findall(r'Post-doc|POSTDOC|Postdoc', string, re.IGNORECASE):
            return ["Post-doc"]
        elif re.findall(r'P[Hh]\.?D', string) and re.findall(r'M\.[SA]|Master|MASTER', string):
            return ["Ph.D.", "Masters"]
        elif re.findall(r'Ph[.]?[ ]*D|DOCTOR|doctor|Doctor|J\.D', string):
            return ["Ph.D."]
        elif re.findall(r'M\.[SA]|Master|MASTER', string) and re.findall(r'Bachelor|B\.[SA]', string):
            return ["Masters", "Bachelor"]
        elif re.findall(r'M[.]A|M[.]S|Master|master|MASTER', string):
            return ["Masters"]
        elif re.findall(r'B[.]A|B[.]S|Bachelor|bachelor|BACHELOR', string):
            return ["Bachelor"]
        elif re.findall(r'scholar', string, re.IGNORECASE):
            return ["Scholar"]
        elif re.findall(r'BS|BA|B\.|Bsc', string):
            return ["Bachelor"]
        elif re.findall(r'MS|MA|MPH|M\.[A-Z]|Msc|MR', string):
            return ["Masters"]
        return None

    @staticmethod
    def institution_parser(string):
        institution_hierarchy = [r'Universi|UNIVERSI', r'College|COLLEGE', r'Institut|INSTITUT', r'Center|CENTER',
                                 r'UC', r'School|SCHOOL', r'Polytech|polytech|POLYTECH', r'Academy|academy']
        for institution_type in institution_hierarchy:
            if re.findall(institution_type, string):
                text_list = re.split(r'[,.;:()]|(?:\s+\-\s+)', string)
                for pos, val in enumerate(text_list):
                    if len(val) >= 56:
                        continue
                    if re.findall(r'university of california$', val, re.IGNORECASE) \
                            and pos != len(text_list) - 1:
                        val += ',' + text_list[pos + 1]
                        return [re.sub(r'^[^a-zA-Z]*|[0-9]| *$', '', val)]
                    if re.findall(institution_type, val):
                        return [re.sub(r'^[^a-zA-Z]*|[0-9]| *$', '', val)]
        return None

    @staticmethod
    def year_parser(string):
        text = re.sub(r'present|progress', 'NOW', string, flags=re.IGNORECASE)
        text_list = re.findall(r'NOW|(?:19|20)[0-9]{2}.{,8}[-|to]{1,3}.{,8}NOW|'
                               r'(?:19|20)[0-9]{2}.{,8}-{1,3}.{,8}(?:19|20)[0-9]{2}|(?:19|20)[0-9]{2}', text)
        if text_list:
            year_list = []
            for val in text_list:
                if 'NOW' in val:
                    year_list.append('NOW')
                    continue
                elif re.findall(r'-', val):
                    year_list.append(re.findall(r'(?:19|20)[0-9]{2}', val)[1])
                    continue
                elif re.findall(r'(?:19|20)[0-9]{2}', val):
                    year_list.append(val)
            return year_list
        else:
            return None


class PubTitleTransformer(FieldParser):
    def __init__(self, dic):
        FieldParser.__init__(self, dic, ['string_refined', 'title_flag', 'hashcode'], 'string')

    def transform(self):
        string_refined_list = re.findall(r'\"([^\"]+)\"', self.record_dict[self.identifier])
        if string_refined_list and len(re.split(r' +', string_refined_list[0])) >= 10 and \
                not re.findall(r'encyclopedia', self.record_dict[self.identifier]):
            self.record_dict['string_refined'] = string_refined_list[0]
            self.record_dict['title_flag'] = True
        else:
            self.record_dict['string_refined'] = self.record_dict['string']
            self.record_dict['title_flag'] = False
        self.record_dict['hashcode'] = hashlib.sha1((self.dic['string'] + self.dic['filename']).encode()).hexdigest()


class PubCrossrefTransformer(FieldNetworkParser):
    def __init__(self, dic):
        FieldNetworkParser.__init__(self, dic, {**crossref_first_mapping, **crossref_second_mapping}, 'string_refined',
                                    'http://search.labs.crossref.org/dois?q=%s' % dic['string_refined'], None,
                                    'response_code_c')

    def transform(self):
        direct_doi = re.findall(r'10[.][0-9]{4,}(?:[.][0-9]+)*/(?:(?!["&\'<>,])\S)+', self.record_dict['string'])
        # r'10[.][0-9]{4,}/[0-9a-zA-Z\-./]+'
        if direct_doi:
            self.record_dict['first_doi'] = 'http://dx.doi.org/' + direct_doi[0]
            self.record_dict['second_doi'] = 'DEFINITE'
            return

        data = self.resp.json()
        if not data:
            return
        data = unicode_wrapper(data)

        for key, val in crossref_first_mapping.items():
            self.record_dict[key] = data[0][val]

        if len(data) > 1:
            for key, val in crossref_second_mapping.items():
                self.record_dict[key] = data[1][val]


class PubScopusTransformer(FieldNetworkParser):
    def __init__(self, dic):
        if dic['first_doi']:
            url = "http://api.elsevier.com/content/search/scopus?query=DOI(%s)&view=COMPLETE" % \
                  '/'.join(re.split(r'/', dic['first_doi'])[3:])
        else:
            url = None
        FieldNetworkParser.__init__(self, dic, {**scopus_mapping, **{'s_author_id': None, 's_affiliation_id': None,
                                                                     's_current_author_id': None}},
                                    'first_doi', url, {'Accept': 'application/json', 'X-ELS-APIKey': API_KEY_KIM},
                                    'response_code_s')

    def transform(self):
        data = self.resp.json()['search-results']['entry'][0]
        if 'error' in data.keys():
            return
        data = unicode_wrapper(data)

        for key, val in scopus_mapping.items():
            self.record_dict[key] = data.get(val)

        if data.get('author'):
            self.record_dict['s_author_id'] = ';'.join(val.get('authid') for val in data['author'] if val.get('authid'))
            self.record_dict['s_current_author_id'] = self.get_current_auth_id(data['author'])
        if data.get('affiliation'):
            self.record_dict['s_affiliation_id'] = ';'.join(val.get('afid') for val in data['affiliation']
                                                            if val.get('afid'))

    def get_current_auth_id(self, author_dict):
        author_name_list = []
        for a in author_dict:
            if a['surname'] and a['given-name']:
                author_name_list.append(((a['surname'] + ' ' + a['given-name']).lower(), a['authid']))
            else:
                author_name_list.append((re.sub(r'-', ' ', a['authname'].lower()), a['authid']))
        author_name = (self.record_dict['f_first_name'] + ' ' + self.record_dict['f_last_name']).lower()
        author_name_list = sorted(author_name_list, key=lambda x: fuzz.token_set_ratio(author_name, x[0]), reverse=True)
        author_id = author_name_list[0][1]
        return author_id


class PubDoiParser(FieldNetworkParser):
    def __init__(self, dic):
        FieldNetworkParser.__init__(self, dic, doi_mapping, 'first_doi', dic['first_doi'],
                                    {'accept': 'application/x-research-info-systems'}, 'response_code_d')

    def transform(self):
        data = self.resp.text
        if re.findall(r'^<', data):
            return
        data = unicode_wrapper(data)

        text_list = re.split(r'\n', data)
        for val in text_list:
            if val:
                combination = re.split(r'  - ', val)
                if len(combination) == 2:
                    name, value = re.split(r'  - ', val)
                    if name in list(doi_mapping.keys()):
                        if self.record_dict.get(name):
                            self.record_dict[name] += ';%s' % value
                        else:
                            self.record_dict[name] = value


class PubCompareRatioParser(FieldParser):
    def __init__(self, dic):
        FieldParser.__init__(self, dic, ['relative_compare_ratio', 'absolute_compare_ratio'], 'string')

    def transform(self):
        self.record_dict['relative_compare_ratio'] = fuzz.token_set_ratio(
            self.record_dict['string_refined'].lower(),
            ' '.join(str(val) for val in self.record_dict.values() if val).lower())

        if self.record_dict['TI']:
            if self.record_dict['title_flag']:
                self.record_dict['absolute_compare_ratio'] = fuzz.ratio(
                    self.record_dict['string_refined'].lower(),
                    self.record_dict['TI'].lower())
            else:
                self.record_dict['absolute_compare_ratio'] = fuzz.ratio(
                    self.record_dict['string_refined'].lower(),
                    ' '.join(val for val in [self.record_dict['AU'], self.record_dict['TI'],
                                             self.record_dict['T2'], self.record_dict['DA']] if val).lower())
        else:
            self.record_dict['absolute_compare_ratio'] = -1


class PubJournalExtractor(FieldParser):
    def __init__(self, dic):
        self.database = pd.read_csv('resources/journals/JCR_SCIE_2015.csv')
        FieldParser.__init__(self, dic, journal_mapping.keys(), 'SN')

    def transform(self):
        if ';' in self.record_dict['SN']:
            sn_list = re.split(r';', self.record_dict['SN'])
        else:
            sn_list = [self.record_dict['SN']]

        for sn in sn_list:
            row = self.database[self.database['ISSN'] == sn]
            if len(row) == 1:
                for key, val in journal_mapping.items():
                    self.record_dict[key] = row.get(val).values[0]
                return


class PubAuthIDParser(FieldNetworkParser):
    def __init__(self, dic):
        FieldNetworkParser.__init__(self, dic, author_mapping, 'a_author_id',
                                    'http://api.elsevier.com/content/author?author_id=%s&view=METRICS' %
                                    dic.get('a_author_id'), {'Accept': 'application/json', 'X-ELS-APIKey': API_KEY_KIM},
                                    'response_code_a')

    def transform(self):
        data = self.resp.json()["author-retrieval-response"][0]
        for key, val in author_mapping.items():
            if '+' in val:
                val1, val2 = re.split(r'\+', val)
                self.record_dict[key] = data.get(val1).get(val2)
            else:
                self.record_dict[key] = data.get(val)


class GrantFieldParser(FieldParser):
    def __init__(self, dic):
        FieldParser.__init__(self, dic, grant_mapping.keys(), 'string')

    def transform(self):
        for key, val in grant_mapping.items():
            if re.findall(val, self.record_dict['string']):
                self.record_dict[key] = self.record_dict['string']
                return


class FieldFilter(FieldParser):
    def __init__(self, record_dict):
        FieldParser.__init__(self, record_dict, ['filter_flag'], 'string')


class PubFieldFilter(FieldFilter):
    def transform(self):
        string = self.record_dict['string_refined']
        self.record_dict['filter_flag'] = False
        if len(re.split(r' +', self.record_dict['string'])) <= 2:
            return
        if self.record_dict['second_doi'] == 'DEFINITE':
            self.record_dict['filter_flag'] = True
            return
        if not self.record_dict['second_title'] or self.record_dict['first_normalized_score'] < 45:
            return
        if self.record_dict['first_normalized_score'] > 80 \
            or self.record_dict['first_title'] and \
            fuzz.partial_ratio(self.record_dict['first_title'].lower(), string.lower()) > 75 \
            or self.record_dict['first_full_citation'] and \
            fuzz.partial_ratio(self.record_dict['first_full_citation'], string.lower()) > 80 \
            or self.record_dict['second_title'] and \
            fuzz.partial_ratio(self.record_dict['first_title'], string.lower()) > \
                2.5 * fuzz.partial_ratio(self.record_dict['second_title'], string):
            if self.record_dict['relative_compare_ratio'] > 50 and self.record_dict['first_score'] > 1.8 \
                and (not self.record_dict['AU'] 
                     or self.record_dict['f_last_name'].lower() in self.record_dict['AU'].lower()):
                self.record_dict['filter_flag'] = True
        else:
            return


class GrantFieldFilter(FieldFilter):
    def transform(self):
        if any([self.record_dict[val] for val in grant_mapping.keys() if self.record_dict[val]]):
            self.record_dict['filter_flag'] = True
            return
        else:
            self.record_dict['filter_flag'] = False


class FieldParserHelper:
    def __init__(self, record_dict, field_parser_list):
        self.record_dict = record_dict
        self.field_parser_list = field_parser_list
        self.column_list = []
        self.make_dictionary()

    def make_dictionary(self):
        for field_parser in self.field_parser_list:
            field_transformer = field_parser(self.record_dict)
            self.record_dict = field_transformer.record_dict
            self.column_list = list(self.record_dict.keys())


if __name__ == '__main__':
    partition_name = 'publication'
    columns = ''
    fake_dict = {'filename': '6_15_286_11600_Chang_Kiyoung.pdf',
                 'string': 'Poxviral VP11: A Big Role for a Small Protein. Reddy,'}
    fake_auth_dict = {'a_author_id': '16643916900'}

    if partition_name == 'publication':
        field_parsers = [TitleTransformer, PubTitleTransformer, PubCrossrefTransformer, PubDoiParser,
                         PubScopusTransformer, PubCompareRatioParser, PubJournalExtractor, PubFieldFilter]
        columns = sorted(FieldParserHelper(fake_dict, field_parsers).column_list + ['no_parsed', 'no_received'] +
                         FieldParserHelper(fake_auth_dict, [PubAuthIDParser]).column_list)
    elif partition_name == 'grant':
        field_parsers = [TitleTransformer, GrantFieldParser, GrantFieldFilter]
        columns = sorted(FieldParserHelper(fake_dict, field_parsers).column_list)
    elif partition_name == 'education':
        field_parsers = [TitleTransformer, EduFieldParser]
        columns = sorted(FieldParserHelper(fake_dict, field_parsers).column_list)

    print(','.join(columns))
