## Overview

This parser is designed to extract useful information from CV. Useful information may be anything, but in this parser, we mean structured data, such as education information or publication information. Currently, the parser can extract and parse three kinds of information: Education, Publication and Grant. To better illustarte the idea, I split the parsing process into three levels:

1. Partition Level. In this level, the parser will try to find the top-level tags (we call it partitions), and split the CV into different partitions. For example, education, scholarship and publication can all be partitions.
2. Section Level. In this level, the parser will parse each partition and find their inner structures. Each record in called a section. For example, a publication string in a publicaiton partition is called a section, or a publication section.
3. Field Level. In this level, the parser will read each section and connect to a database or use some criterion to find each field we want. For example, for a publication section, we may be interested in the authors, the title and some other fields. All of them belong to the field level.

This documentation is organized with the following logic: It will state the libraries or tools used first, and then explain the procedures in each of the three levels. In each of them, you will see the detailed steps, and the reason of doing it, including the tradeoff or balances I have made during development. 

Please be noted that parsing a CV is not a easy job at all. Different CVs have different formats, and it is impossible for a parser to consider all potential circumstances. Computers are not humans: they can only recognize very good data. All that can be done is to parse those CVs that are well-formated or some wired formats I have found so writing programs to deal with.

I will also hide the coding style and techniques and focus on the logic behind the parser in this documentation.

## Libraries and Languages

#### Libraries

This parser is built on top of popper, which is a library that builds on top of Linux's pdftohtml command. With Poppler, a pdf file can be transformed into a xml file, which can preserve much of the position information of the pdf file. The position information can be used to parse different texts into different groups, and further information extraction.

#### Languages

This parser use Python as the main languages, and very little bash scripts and json files. Below are the Python packages used in this parser.

+ re: Python Standard Library for Regular Expression support
+ logging: Python Standard Library for logging
+ datetime: Python Standard Library for Standardizing date and time format
+ requests: Third-party library to Connect to remote database and get outputs
+ fuzzywuzzy: Third-party library to compare distance between two strings
+ nltk: Third-party library for Words statistics summary
+ numpy: Third-party library for Scientific calculation and format support
+ pandas: Third-party library for Dataframe support
+ sqlAlchemy: Third-party library for Python SQL ORM
+ unidecode: Third-party library for Unicode encoding support

## Partition Level

This is the first level, top most level for the parser. As is said earlier, the parser finds the top level tags as different partitions. During this explanation, I will call the name of each partition as a header. A header list is built in advance manually, which consists of many frequently emerged, potential headers, such as education, publication, scholarship, articles and so on. Afterwards when I say a word is a valid header, it means that this word can be found in this header list, and satisfy other requirements, including the number of words should be no longer than 8, and starting with an alphabet.

#### Terminologies

Before the explanation of the logic of partition level, here are some terminologies from xml file of poppler:

+ text: the atomic element in xml file. It consists of all the information: words, font, left, height, top, width.


+ font: Different text have different fonts. A font can be differed in size and font type. Ranging from 1 to some integer value.
+ left: The distance from the start of the text to the left margin of the pdf file.
+ height: The height of the words in the text.
+ top: The distance from the ceiling of the text to the top margin of the pdf file.
+ width: The length of the words of the text.

Here are the steps:

#### Preprocessing

What we have is only a pdf file. So the first step is transform it into xml file, using poppler. Next are some steps to modify a raw xml file into a ready-to-process xml file.

1. First Rearrange all the items since some of them maybe ordered in a way that is difficult to parse when it is created. Our hope is that the items should be ordered based on their positions on tha page, from the top to the bottom. we reorganize the items based on the "top" attribute.
2. If more than then underscores(_) can be found in a text, remove all of them, and reduce its width to 100, since it is highly possible that this text should be a partition header.
3. If the words of a text is separated by spaces for at least 4 times, identify it as a header.
4. Depending on the distance between two lines:
   1. If the distance is small than a normal value, it is probably that they should belong to the same text, but for some reasons (e.g., different fonts), they are separated. There may exist a special situation where a the start of a word is capitalized. If it is indeeded this situation, and this word is a valid header, identify it as a header. Otherwise, just append the text to the previous text.
   2. If the distance is very negative, meaning the next text is above the previous line, append the previous text to the text before the previous text. The parser is doing so because the preprocessing procedure will move on and I need to accomplish the remaining tasks to the previous text.
   3. If the distance is normal, most of the time the procedure will move on, except for some rare situation, which identifies the current text should be appended to the previous one.
5. Substitute multiple spaces with one space, remove empty text line, and transform encoding to UTF-8.

#### Get the header

Now the texts are much cleaner, and we should group them based on different critertions: the font value, the left value, the height value and the width value. The basic idea under grouping is that, for a group of headers, they should have identical formats. The most robust format to identify header group should be font, but there are also other methods when font group fails to identify the header group. Below are the methods used in order, which means if the previous one can identify the header group, the latter ones will not be used. Another thing need to know is that I always look at the top value based on some criterion for each method. If there is a tie, use the next approach:

1. If some texts have been identified as a header in the preprocessing procedure above, they should be the headers.
2. If all texts from a font group all start with a capitalized letter and at least 5(30%) are valid headers, return a successful match. The criterion is the number(ratio) of valid headers.
3. If all texts from a font group have the largest header ratio and the value is at least 0.3, return a successful match. The criterion is the ratio of valid headers compared to all texts for each font group.
4. If all texts from a left group have the largest header ratio and the value is at least 0.25, return a successful match. The criterion is the ratio of valid headers compared to all texts for each left group.
5. If all texts from a height group have the largest header ratio and the value is at least 0.25, return a successful match. The criterion is the ratio of valid headers compared to all texts for each height group.

I need to clarify that all the criterion thresholds are set by experiments. I looked at many test files and found the values the parser is using now should be the most appropriate one. They are hard codes, but they cannot be avoided. I need them to extract the headers, and keep a balance between false positives and true negatives. For all hard threshold I will mention in the rest of the documentation, they are all set in this manner.

The way that defines valid headers here may be slightly different with the valid headers defined above. But most of them are identical. Please see code for more details.

But there are some special treatments. Since we are particularly interested in education and publication, the parser set some special words that needs to emerge in the headers. If the parser does not see them, the parser will look deeply into other correpsonding groups, with a very strong criterion in case of adding false positive ones. 

#### Return Partition texts

Now we have the headers, together with their relative position in all the texts. The headers partition the xml into different partitions, and that's why we call it partition level. Now we need to extract all partition texts associated with a particular partition.

One partition may have multiple partition words, for example, the partition education consists of two partition words: education and academic. Selecting a proper set of partition words needs a bunch of tests: I did all these manually by first thinking of some potential words and see their performance. At last select the appropriate ones.

Now the search begins in the headers. If a header matches a partition word, the parser will extract the texts belonging to it and pass them to section level. For a partition that has multiple partition words, the texts are processed by section level parser group after group.

What needs a special consideration is that, typically we think the file type should be a resume, but sometimes it is a publication only. Then, if we are parsing the publication, we can directly sent the result to the section level, without doing the partitioning process.

## Section Level

The parser implements three sections now: Education, Publication and Grant. I will first explain the general logic for all of them, and the specific configurations for each of them.

#### General logic

For a section, the parsing process is as follows:

1. Find the inner structure of the partition. This is done by using a section sub parser. A section sub parser is written to use some algorithm to split the partition into different sections, by calculating the starting index and ending index of the partition. Different section sub parsers apply to different situations, and use different text attributes. Currently there are three section sub parsers:

   + Identifier parser. This only applies to education partition. The parser first tries to find year, degree and institution by order, and if any one is found, then use that identifier to split the partition into different sections. If none of the three identifiers are found, this parser will force to use year as the identifier.
   + Paragraph parser. This applies to education, publication and grant partition. It uses the top attributes to calculate the distances between any two continuous pairs of texts. Page breaks are also considered here. Then the top distance is counted and some potential paragraph break distances are found then tests are run on each of them to get the most probabal one. Then any distances that are larger than this paragraph break threshold are considered different paragraphs, and then are separated into different sections.
   + Left parser. This applied to publication and grant partition. Some CVs use the left identation to organize each item. So the left parser uses the left attributes to get the left most value and compare to the second left most value, and if the statistics of both of them pass some tests, they are considered satisfy the left indentation property, and texts with the attribute of left value identical to the left most one are thought to be the start of a section. The tests include their ratio value and absolute value, if you are interested in it, please refer to the codes.

   For each partition, multiple section sub parsers are used to ensure it can return separated sections. This means that if the previous section sub parser can parse this partition as valid results, the latter one will not be used, as what is explained in partition parser. The sections are passed to the analyzers.

2. Analyzers are responsible to parse each section into valid fields. In other words, a analyzer will first do some preprocessing to a section and then feed it to field parser, get the result and at last store it for further processing. The result from a analyzer may be valid or invalid, and the way to check whether it satisfies the criterion is done in checker.

3. Checkers are used to determine whether the result from analyzers are valid. If it is valid, then the result will be returned as final results; if not, the next section sub parser is used with the same process. If none of the results from all section sub parser are valid, all of the results will be passed to resolver to merge them.

4. Mergers are designed to merge all results from different section sub parser, and give a good result. It will dig into the structure of each potential results and applies different algorithms based on different partitions.

5. The multiple resolver is used to create a empty result if none is found to fill up the hole. If there is no multiple resolver, then if for some reason the result cannot be generated for a particular file, there will be no record for that file.

For different partition, the analyzer, check and merger may differ from the others significantly. It is time to look into each of the partition implementation details.

#### Education Partition

For each of the three partition, I will only discuss their specific details.

1. Section Sub Parser: Identifier Parser and Paragraph Parser, which has been talked about above.

2. Analyzer: For each section, first concatenate the all strings in the texts of this section altogether into a very big string. Feed this string to the field parsers to extract all needed fields.

3. Checker: The checker will see whether all fields are filled in and no empty fields.

4. Resolver: The result are coming from identifier parser and paragraph parser. If there is no result from identifier parser, the result from the paragraph parser will be used. Otherwise, the education parser thinks that the identifier parser is more robust, so it will look into each section result, and see whether it lacks any information. If it finds one, it will look into the paragraph parser result and see whether the already existing fields in identifier parser result can be found in the paragraph parser result. If so, it will fill the missing field with the one found.

5. Multiple Resolver: Identical as default one.

#### Publication Partition

1. Section Sub Parser: Left Parser and Paragraph Parser.

2. Analyzer: For each section, first concatenate the all strings in the texts of this section altogether into a very big string. Then the string is passed to field parser to get all the relevant information we want. At last, the analyzer will count how many are successfully parsed based on the returned results.

3. Checker: The checker will only check whether this result is empty. If not empty, the publication parser thinks it is valid, otherwise invalid.

4. Resolver: The resolver will only return the non-empty result. If both are empty, empty will be returned. For this case, it is highly possible that the partition parser fails to work.

5. Multiple Resolver: Since there are many cases that the publication parser fails: the partition parser fails, the strings cannot be matched or other reasons, I have included the number parsed and number received for each file, so different status code can be stated here indicating different reasons for empty result.

#### Grant Partition

1. Section Sub Parser: Left Parser and Paragraph Parser.
2. Analyzer: For each section, first concatenate the all strings in the texts of this section altogether into a very big string. Then the parsed results will be stored to check.
3. Checker: The checker will only check whether this result is empty. If not empty, the grant parser thinks it is valid, otherwise invalid.
4. Resolver: The resolver will only return the non-empty result. If both are empty, empty will be returned. For this case, it is highly possible that the there is no grants for this CV.
5. Multiple Resolver: Identical as default one.

## Field Level

Now the last step is the field level parser. We use the pipeline model to do the field parsing job. 

So what does pipeline means? Anyone who is familiar with Unix should be aware of pipeline: pass in an input and expect an output. Here the inputs and outputs are always dictionaries. So they are communicated on the same protocol: pass in a dictionary and pass out a dictionary, as well. Since it is designed this way, the order of the pipeline should not matter. But some fields may depend on the value of others, so we add a check named identity to check whether this field is present or not. If it is present, this pipeline will be used to add new fields, otherwise, this pipeline will be skipped and the dictionary will be feed to the next stage. The reason is that, sometimes, some particular field may be parsed with no value due to many reasons, and to keep the programming running without any unexpected errors, the empty fields will be neglected and the program continues.

For some of the results got from the Internet, there may exist some encoding problems. So before parsing processing, it will first be transformed to UTF-8.

#### General Logic

Before started, I need to give a description of the general logic here.

The first pipeline is always the title transformer, since it will extract the fields from the filename. This pipeline is essential.

The subsequent steps are not general, but all the pipelines are capusulated into a list of pipelines and they will run in order.

In the specific description below, I will tell the implementations for each fields.

#### Education Fields

1. This is only one pipeline for the education field, because the education strings cannot be separated in an easy way. The reason is, some of the information may be mixed into a very large section of texts. The logic is, with the splitted fields, for each of them, check whether the degree is found. Typically we think a valid degree must at least has degree information, and other fields may not be listed. 

   The mixes may include, for example, the author of the CV may get multiple degrees from the same institutions. So when the parser can only see a small number of institutions compared to the number of degrees, it will auto fill the institutions with the higher educations.

   The results will be stored as potential final results if it has degree name and at least year or institution information.

   Next I will describe the detailed extracted methods used in each of the three fields.

2. Degree Fields: The degree is found recursively with this order: Post-doc, Phd, Master, Bachelor, Scholar. There are many criterions set in order so it will match from the most robust one to the least robust one.

3. Institution Fields: There are many types of universities. A potential university can include names with university, college, center, school or polytech. The names are also set in order from the most possible one to the least possible one. Another special treatment which is done here is, since this parser is built on uc universities, when university of california is encountered, it will look for the next word for the campus information.
4. Year Fields: There are many types of year, including 19xx, 20xx, xx, and the starting and the ending year can be separated by hypen(-) or to. The year parser needs to accomodate all possible situations. Another thing that needs to be considered is, the word present or progress, which means a time now. So the parser create a new identifier, named NOW, to indicate this kind of time.

#### Publication Fields

There are many pipelines here. So let me introduce them one by one:

1. Publication Title Transformer: Then try to extract the title. A string is considered as a title if it is enquoted with the big string, and it is the only string that is enquoted. If the title is found, the publication analyzer will use the title (called pub) for subsequent task, otherwise the whole string will be used. Also a hashcode will be generated for matching and checking availability.

2. Crossref Transformer: We give the title to crossref to let it give us a very long list of possible publications, with their absolute and relative scores. We will keep record of the first match and the second match, along with all their statistics, including the doi, score, citation and so on.

   What needs to be mentioned here is that, if the doi number can be found directly within the title, it will be used definitely, and we will not connect to the crossref database.

   Since it is a remote database, network connection is needed. So, to make sure that the connection is always working, we will log the connection status as well as checking the response code. If all passed through, the program will proceeds, otherwise, it will connect for at most five times, and after which a failed connection will be identified.

3. Doi.org Transformer: This is a database can return most of the fields that are needed, including author name, datetime, journal name, publication title and so on. We use this to get a formatted result: RIS format. From the RIS format, the regular expressions are written to parse the result. It is a formatted result, so it is much easier to get parsed, as well as having very accurate information.

4. Scopus Tranformer: Scopus will reveal other information that is not included in the doi.org and crossref. The API is very good and the result is already in json format, which makes it need little effort to parse.

   Another procedure done here, is to extract the author information. Typically we need the author id in Scopus, and this information can be got directly in the publication. We will look for the maximum match as the identified id, and with it we can query Scopus Author Retrieval for more information.

   Attention here: We have quota on the Scopus API, so we should be conservative to using them.

5. Compare Ration Transformer: Here we will check the result from remote database with the string on the title side. Depending on whether the parsed result has title and whether the title is extracted, this process is handled in different ways.

6. Journal Transformer: Here the journal database is connected to extract relevant information.

7. Publication filter: We will use the relative score to determine whether it should be selected. If the relative score is high, it will be selected, otherwise it will compare to the string with the title from crossref. It the compare ratio is high, it will be selected. Or if the ratio or score is high compared to the second result, it will be selected as well. The reason of doing so is that, we think the only possible result should be the first one. If the first one cannot satisfy our requirements, it should be a mismatch. If the match score or distance of the second match is close to the first one, we think that the match is not accurate, so it will be discarded as well. If there is a successful match, it will return the matched DOI, otherwise no data. We use DOI because it is a unique identifier to extract metadata from other databases, and is accepted across all databases. There are many hard coded thresholds, as the same logic as previous hard coded ones.

   Noted that if the doi is got from regular expression, it will definitely pass the filter.

#### Grant Fields

1. Grant Parser: We think that a string can be at most one grant, so a record will be no grant, or one grant. Then based on a list of potential grants, the string will be feed to the field parser to match each of them. The criterion here is very strict since most of the time, the grants should be proper nouns. If no grant is found, no result will be returned.

   For each possible grant, they are searched one by one. Although there is an order between them,any string can be at most one grant. So a grant will be matched sooner or later, regardless of the order.

2. Grant Filter: if any grant is found, the result will be kept. Otherwise, discarded.

## Summary

This is the logic of the parser. This documentation is not served as a tutorial, and is served as a manual to explain the logic of the process, and the reason for each process. This parser is modifing from time to time, as long as I see any bugs.

The coding style is omitted in this documentation. Actually I use many design patterns, such as Interfaces, Classes, Decorators to make the code easier to read and modify. Many features of functional programming languages are also used.



Zhen Zhang,

Graduate Student Researcher in UC Davis,

October 2016
