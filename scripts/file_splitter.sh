#!/bin/bash

OLDDIR=$1; NEWDIR=$2
c=0; d=1; DIRNAME=CV;
mkdir -p ${NEWDIR}/${DIRNAME}_${d}
for file in ${OLDDIR}/*.pdf
do
    if [ ${c} -eq 100 ]; then
        d=$(( d + 1 )); c=0; mkdir -p ${NEWDIR}/${DIRNAME}_${d}
    fi
    cp "$file" ${NEWDIR}/${DIRNAME}_${d}
    c=$(( c + 1 ))
done

# Sample Usage:
# file_splitter.sh OLDPATH NEWPATH
