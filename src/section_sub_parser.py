import nltk
from itertools import chain
from functools import wraps
from CVCodingTool.src.field_parser import EduFieldParser
import re


def education_identifier_parser(texts):
    """
    This is the second parser for education. It is simpler than the first one (the main one).
    The logic is as follows:
    STEP I:
    It will scan from the beginning of the texts, and see the structure of each part. The
    job is looking for the identifier, which can be year, degree and institution. Typically
    I think the one emerges in the first line should be the identifier, or first comes into
    being. Then the parser will use it to locate the structure, where I call it section.
    STEP II:
    Since it is using the beginning as the identifier, when expanding it to the partition,
    it will be structured as the begin index of the section partitioner.

    :param texts: text object in xml.
    :return: return section partitioner. Each partitioner should be two integers indicating
             the beginning and end of the index of text object. It should be lists nested in
             a big list.
    """
    # STEP I:
    edu_parser = EduFieldParser({})
    field_parsers = [edu_parser.year_parser, edu_parser.degree_parser, edu_parser.institution_parser]
    partition = []
    parser = None
    for parser_test in field_parsers:
        if len(texts) > 1:
            if parser_test(' '.join([texts[0].text, texts[1].text])):
                parser = parser_test
                break
    if not parser:
        parser = field_parsers[0]
    for pos, text in enumerate(texts):
        if parser(text.text):
            partition.append(pos)
    # STEP II:
    if not partition:
        return None
    off_pos = partition[0]
    sections = []
    for pos, val in enumerate(partition):
        if pos == 0:
            begin_index = 0
        else:
            begin_index = val - off_pos
        if pos == len(partition) - 1:
            end_index = len(texts)
        else:
            end_index = partition[pos + 1] - off_pos
        sections.append([begin_index, end_index])

    return sections


def section_reducer(f):
    @wraps(f)
    def inner_func(texts):
        sections = f(texts)
        if not sections:
            return sections
        new_sections = []
        for section in sections:
            if section[1] - section[0] > 5:
                new_section = f(texts[section[0]:section[1]])
                # if not new_section or len(new_section) == section[1] - section[0]:
                if not new_section:
                    new_sections.append(section)
                else:
                    new_sections += [[va + section[0] for va in val] for val in new_section]
            else:
                new_sections.append(section)
        return new_sections

    return inner_func


@section_reducer
def section_paragraph_parser(texts):
    """
    Compared to the second sub-section parser, this one is complicated.
    The logic is as follows:
    STEP I:
    Please keep in mind that each degree along with other information should be closely
    together compared to other degrees. In other words, it should form different paragraphs.
    Since it aims to find the paragraph structure, it will look at the top attribute. Do
    the first order difference will see the distance from the above and the below texts. Then
    it will count the frequency along with the indices belonging to that top attribute.
    After that, I know the structure distance should be only between 24 and 48 (less to 0 is
    invalid and must be excluded, and more to 48 is alo possible, this is a trade-off). I will
    also do unclear matching, and also length check. Since I think the number of degrees should
    always be less or equal to four (of course possible 5, 6... but they are rare. Trade-off as
    well), if the frequency is larger than 3 (the separation, which is one less than sections),
    I will make it the partitioner, otherwise it will still search in the list.
    STEP II:
    Whenever I encounter the right one, it will be used to expand the partitioner. It is the end
    index, different from the second identifier partitioner.
    ATTENTION:
    24, 48 are empirical figures. In other words, they are hard coded.

    :param texts: text object in xml.
    :return: return section partitioner. Each partitioner should be two integers indicating
             the beginning and end of the index of text object. It should be lists nested in
             a big list.
    """
    # STEP I:
    if len(texts) == 1:
        return [[0, 1]]

    top_attrs = [int(text.get('top')) for text in texts]
    top_diff = [x[0] - x[1] for x in zip(top_attrs[1:], top_attrs[:-1])]
    page_break_ids = [pos + 1 for pos, val in enumerate(top_diff) if val < -100 if int(texts[pos].get('width')) < 500]
    top_most_list = nltk.FreqDist(x for x in chain(top_diff, [x - 1 for x in top_diff],
                                                   [x + 1 for x in top_diff])).most_common()
    counter = 0
    top_most = top_most_list[counter][0]
    while counter < len(top_most_list) - 1 and (top_most <= 5 or top_most >= 55):
        counter += 1
        top_most = top_most_list[counter][0]

    partition = []
    for pos, diff in enumerate(top_diff):
        if 55 >= diff > top_most + 4:
            partition.append(pos + 1)
    if not partition:
        for pos, diff in enumerate(top_diff):
            if 6 <= diff:
                partition.append(pos + 1)
    # partition = [pos+1 for pos, text in enumerate(texts) if int(text.get('width')) < 500]
    partition.append(len(texts))
    partition += page_break_ids
    partition = sorted(partition)

    # STEP II:
    sections = []
    for pos, val in enumerate(partition):
        if pos == 0:
            begin_index = 0
        else:
            begin_index = partition[pos - 1]
        end_index = val
        sections.append([begin_index, end_index])

    return sections


@section_reducer
def section_left_parser(texts):
    star_indicator = [pos for pos, val in enumerate(texts) if
                      re.findall(r'^\* |^[0-9]+[.\)] |^\"[A-Za-z]|^\([0-9]+\)', val.text)]
    if len(star_indicator) / len(texts) > 0.25:
        partition = star_indicator
    else:
        left_attrs = [int(text.get('left')) for text in texts]
        left_freq = nltk.FreqDist(left_attrs)
        partition = []
        if len(left_freq) > 1:
            left_most = dict(left_freq.most_common(2))
            left_identifier = min(left_most.keys())
            right_identifier = max(left_most.keys())
            if sum(left_most.values()) / len(texts) > 0.65 \
                    and 0.2 < left_most[left_identifier] / left_most[right_identifier] < 2.4 \
                    and not [val for val in left_freq.keys()
                             if left_freq[val] > left_freq[left_identifier] if val < left_identifier]:
                for pos, val in enumerate(texts):
                    if int(val.get('left')) == left_identifier:
                        partition.append(pos)
            else:
                return None
        else:
            return None
    sections = []
    for pos, val in enumerate(partition):
        begin_index = val
        if pos == len(partition) - 1:
            end_index = len(texts)
        else:
            end_index = partition[pos + 1]
        sections.append([begin_index, end_index])
    if len(sections) == 1:
        return None
    return sections
