data_source=/home/research/ucrecruit/stem_cv/original
data_split=/home/research/ucrecruit/stem_cv/split
data_parsed=/home/research/ucrecruit/stem_cv/parsed

clean:
	rm -rf results/failed/* results/parsed/* results/log/*

education:
	python main.py -p education -d server

publication:
	python main.py -p publication -d server

education_test:
	python main.py -p education -d server_test

publication_test:
	python main.py -p publication -d server_test

file_name_preprocess:
	find ${data_source} -name "*[ \`\'\(\)]*.*" -type f -print0 | while read -d $'\0' f; do mv -v "$f" "${f//[ \`\'\(\)]/}"; done

file_split:
	scripts/file_splitter.sh ${data_source} ${data_split}
