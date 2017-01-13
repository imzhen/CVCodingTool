from itertools import chain
from operator import itemgetter

from CVCodingTool.src.field_parser import *
from CVCodingTool.src.section_sub_parser import section_paragraph_parser, education_identifier_parser, \
    section_left_parser


class SectionParser:
    def __init__(self, texts_list, filename, sub_parsers, header, field_parsers):
        self.filename = filename
        self.sub_parsers = sub_parsers
        self.texts_list = texts_list
        self.header = header
        self.field_parsers = field_parsers
        self.section_each_dict = []
        self.section_dict = []
        self.metadata = TitleTransformer({'filename': self.filename}).record_dict

        for texts in self.texts_list:
            if texts:
                section_sub_dict = self.get_section_sub_dict(texts)
                if section_sub_dict:
                    self.section_dict += section_sub_dict

        self.section_dict = self.multiple_resolver()

    def get_section_sub_dict(self, texts):
        self.section_each_dict = []
        for parser in self.sub_parsers:
            sections = parser(texts)
            if sections:
                section_dict = self.section_analyzer(sections, texts)
                if self.section_checker(section_dict):
                    return section_dict
                else:
                    self.section_each_dict.append(section_dict)
            else:
                self.section_each_dict.append(None)
        return self.section_resolver()

    def section_analyzer(self, sections, texts):
        pass

    def section_checker(self, section_dict):
        pass

    def section_resolver(self):
        return {}

    def multiple_resolver(self):
        if len(self.section_dict) == 0:
            self.section_dict = [dict.fromkeys(self.header)]
            self.section_dict[0]['filter_flag'] = True
        return [{**val, **self.metadata} for val in self.section_dict]


class EduParser(SectionParser):
    def __init__(self, texts, filename, header):
        sub_parsers = [section_paragraph_parser, education_identifier_parser]
        self.check_id = "degree"
        self.needed_id = ["year", "institution"]
        SectionParser.__init__(self, texts, filename, sub_parsers, header, [EduFieldParser])

    def section_analyzer(self, sections, texts):
        section_dict = []
        for val in sections:
            string = ', '.join(text.text for text in texts[val[0]:val[1]])
            field_parser_helper = FieldParserHelper({**{'string': string}, **self.metadata}, self.field_parsers)
            section_dict += field_parser_helper.record_dict
        if len(section_dict) > 7:
            return None
        return section_dict

    def section_checker(self, section_dict):
        check_list = chain.from_iterable((itemgetter(idx)(val) for idx in self.needed_id) for val in section_dict)
        return len(section_dict) > 1 and all(check_list)

    def section_resolver(self):
        section_sub_dict_final = self.section_each_dict[0]
        if not section_sub_dict_final:
            return self.section_each_dict[1]
        for pos, val in enumerate(section_sub_dict_final):
            for idx in self.needed_id:
                if not val[idx]:
                    change_flag = False
                    for other_dicts in self.section_each_dict[1:]:
                        for small_dict in other_dicts:
                            if small_dict[self.check_id] == val[self.check_id] and small_dict[idx]:
                                section_sub_dict_final[pos][idx] = small_dict[idx]
                                change_flag = True
                                break
                    if not change_flag and pos != 0:
                        section_sub_dict_final[pos][idx] = section_sub_dict_final[pos - 1][idx]
        return section_sub_dict_final

    def multiple_resolver(self):
        if len(self.section_dict) == 0:
            self.section_dict = [dict.fromkeys(self.header)]
        return [{**val, **self.metadata} for val in self.section_dict]


class PubParser(SectionParser):
    def __init__(self, texts, filename, header):
        sub_parsers = [section_left_parser, section_paragraph_parser]
        self.no_parsed, self.no_received = 0, 0
        SectionParser.__init__(self, texts, filename, sub_parsers, header,
                               [PubTitleTransformer, PubCrossrefTransformer, PubDoiParser,
                                PubScopusTransformer, PubCompareRatioParser, PubJournalExtractor, PubFieldFilter])

    def section_analyzer(self, sections, texts):
        section_dict = []
        for val in sections:
            string = ', '.join(text.text for text in texts[val[0]:val[1]])
            field_parser_helper = FieldParserHelper({**{'string': string}, **self.metadata}, self.field_parsers)
            if field_parser_helper.record_dict:
                section_dict.append(field_parser_helper.record_dict)
        self.no_parsed += len([val for val in section_dict if val['filter_flag']])
        self.no_received += len(section_dict)
        if len(section_dict) == 0:
            return None
        return section_dict

    def section_checker(self, section_dict):
        return section_dict is not None

    def section_resolver(self):
        return self.section_each_dict[1]

    def multiple_resolver(self):
        if len(self.section_dict) == 0:
            self.section_dict = [dict.fromkeys(self.header)]
            if self.no_received == 0:
                self.no_received, self.no_parsed = -1, -1
        self.metadata.update({'no_parsed': self.no_parsed, 'no_received': self.no_received})
        total_dict = [{**val, **self.metadata} for val in self.section_dict]

        auth_id_list = [val['s_current_author_id'] for val in total_dict if val['s_current_author_id']]
        if auth_id_list:
            auth_id_checked = sorted(auth_id_list, key=auth_id_list.count, reverse=True)[0]
        else:
            auth_id_checked = None
        auth_dict = PubAuthIDParser({'a_author_id': auth_id_checked}).record_dict
        total_dict = [{**val, **auth_dict} for val in total_dict]

        return total_dict


class GrantParser(SectionParser):
    def __init__(self, texts, filename, header):
        sub_parsers = [section_left_parser, section_paragraph_parser]
        SectionParser.__init__(self, texts, filename, sub_parsers, header, [GrantFieldParser, GrantFieldFilter])

    def section_analyzer(self, sections, texts):
        section_dict = []
        for val in sections:
            string = ', '.join(text.text for text in texts[val[0]:val[1]])
            field_parser_helper = FieldParserHelper({**{'string': string}, **self.metadata}, self.field_parsers)
            if field_parser_helper.record_dict:
                section_dict.append(field_parser_helper.record_dict)
        if len(section_dict) == 0:
            return None
        return section_dict

    def section_checker(self, section_dict):
        return section_dict is not None

    def section_resolver(self):
        return self.section_each_dict[1]
