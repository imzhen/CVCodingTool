#!/usr/bin/env bash

bash scripts/API.sh -s 1 -e 61 -p publication &!
bash scripts/API.sh -s 61 -e 121 -p publication &!
bash scripts/API.sh -s 121 -e 181 -p publication &!
bash scripts/API.sh -s 181 -e 241 -p publication &!
bash scripts/API.sh -s 241 -e 301 -p publication &!
bash scripts/API.sh -s 301 -e 361 -p publication &!
bash scripts/API.sh -s 361 -e 421 -p publication &!
bash scripts/API.sh -s 421 -e 471 -p publication &!
bash scripts/API.sh -s 471 -e 521 -p publication &!
bash scripts/API.sh -s 521 -e 568 -p publication &!

awk 'FNR > 1' grant*.csv > bigfile.csv
sed -in '1i ....' bigfile.csv