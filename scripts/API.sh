#!/usr/bin/env bash

setopt rm_star_silent
data_source=/home/research/ucrecruit/stem_cv/original
data_split=/home/research/ucrecruit/stem_cv/split
data_parsed=/home/research/ucrecruit/stem_cv/parsed

if [ ! -d data/results ]; then
    mkdir -p data/results
fi
if [ ! -d data/fail ]; then
    mkdir -p data/fail
fi
if [ ! -d log ]; then
    mkdir -p log
fi
if [ ! -d ${data_split} ]; then
    bash sripts/file_splitter.sh ${data_source} ${data_split}
fi

while [[ $# -gt 1 ]]
do
    key="$1"
    case ${key} in
        -s|--start) START="$2";shift;;
        -e|--end) END="$2";shift;;
        -p|--partition) PARTITION="$2";shift;;
        *) ;;
    esac
    shift
done

counter=${START}

echo "Welcome to the CVCodingTool API!"
echo "This is the real version to be executed. So once it get executed, it will execute for a very long time."
echo ""

echo "All right, let's start."
# make clean
echo "This time, the part $PARTITION will be parsed."
echo ""

while [[ ${counter} -lt ${END} ]]
do
    echo "Parsing Files for at Partition $counter"
#    sed -r -i "s/CV_[0-9]+/CV_${counter}/" config.json
    python main.py -p ${PARTITION} -d server_test --dir ${data_split}/CV_${counter}
    counter=$(( counter+1 ))
done

mkdir -p ${data_parsed}/${PARTITION}/results
mkdir -p ${data_parsed}/${PARTITION}/fail
mkdir -p ${data_parsed}/${PARTITION}/log
cp -r data/results ${data_parsed}/${PARTITION}/results
cp -r data/fail ${data_parsed}/${PARTITION}/fail
cp -r log ${data_parsed}/${PARTITION}/log

echo "This email is sent to confirm that the job with partition $PARTITION is done, with interval from $START to $END" | mail -s "CVCodingTool Running Result" imzhenr@gmail.com


