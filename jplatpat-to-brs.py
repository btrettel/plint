#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <https://stackoverflow.com/a/68612842>

import argparse
import csv

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser(description="extracts all patent document numbers from a JPlatPat search CSV output and puts them in BRS format")
parser.add_argument("input_file", help="JPlatPat CSV file to read")
parser.add_argument("output_file", help="file to output")
parser.add_argument('--version', action='version', version='%(prog)s version 2022-07-01')
args = parser.parse_args()

input_reader = csv.DictReader(open(args.input_file, encoding="utf8"))
dids = set()
for row in input_reader:
    if row['Publication number'] != '':
        dids.add(row['Publication number'])
    
    if row['Registration number'] != '':
        dids.add(row['Registration number'])

pe2e_dids = set()
for did in dids:
    
    if did.startswith('WO'):
        pe2e_dids.add(did.replace(',', '').replace('/', ''))
    else:
        assert did.startswith('JP')
        if '(' in did:
            end_year = did[did.index('(')+1:did.index('(')+5]
            assert end_year.isdigit()
            assert len(end_year) == 4
            end_year = int(end_year)
            
            if end_year < 1989:
                emperor_string = 'S'
            elif end_year == 1989:
                emperor_string = 'SH'
            elif end_year < 2000:
                emperor_string = 'H'
            else:
                emperor_string = ''
        else:
            emperor_string = ''
        
        kind_code = did.split(',')[-1].split('(')[0][0]
        assert kind_code.isalpha()
        
        center = did.split(',')[1]
        if '-' in center:
            center_first  = center.split('-')[0]
            center_second = center.split('-')[1]
            assert center_first.isdigit()
            assert center_second.isdigit()
            
            if emperor_string == 'H':
                assert int(center_first) >= 1
                assert int(center_first) <= 11
                
                pe2e_dids.add('JP'+emperor_string+center_first+center_second+kind_code)
                pe2e_dids.add('JP'+center_first+center_second+kind_code)
                
                if center_second[0] == 0:
                    center_second = str(int(center_second))
                    pe2e_dids.add('JP'+emperor_string+center_first+center_second+kind_code)
                    pe2e_dids.add('JP'+center_first+center_second+kind_code)
            elif emperor_string == 'S':
                assert int(center_first) >= 1
                assert int(center_first) <= 64
                
                pe2e_dids.add('JP'+emperor_string+center_first+center_second+kind_code)
                pe2e_dids.add('JP'+center_first+center_second+kind_code)
                
                if center_second[0] == 0:
                    center_second = str(int(center_second))
                    pe2e_dids.add('JP'+emperor_string+center_first+center_second+kind_code)
                    pe2e_dids.add('JP'+center_first+center_second+kind_code)
            elif emperor_string == 'SH':
                assert (int(center_first) == 1) or (int(center_first) == 64)
                
                pe2e_dids.add('JPS64'+center_second+kind_code)
                pe2e_dids.add('JPH01'+center_second+kind_code)
                pe2e_dids.add('JPH1'+center_second+kind_code)
                
                if center_second[0] == 0:
                    center_second = str(int(center_second))
                    pe2e_dids.add('JPS64'+center_second+kind_code)
                    pe2e_dids.add('JPH01'+center_second+kind_code)
                    pe2e_dids.add('JPH1'+center_second+kind_code)
            else:
                assert int(center_first) >= 2000
                assert int(center_first) <= 2100
                
                pe2e_dids.add('JP'+center_first+center_second+kind_code)
                if center_second[0] == 0:
                    center_second = str(int(center_second))
                    pe2e_dids.add('JP'+center_first+center_second+kind_code)
        else:
            assert center.isdigit()
            pe2e_dids.add('JP'+center+kind_code)
            
            if center[0] == 0:
                center = str(int(center))
                pe2e_dids.add('JP'+center+kind_code)

with open(args.output_file, 'w') as f:
    
    f.write('(')
    start = True
    for pe2e_did in pe2e_dids:
        if not(start):
            f.write(' | ')
        else:
            start = False
        f.write(pe2e_did+'$')
    f.write(').did.')