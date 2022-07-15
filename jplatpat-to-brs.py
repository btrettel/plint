#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# jplatpat-to-brs.py
# Copyright (C) 2022 Ben Trettel
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.

import argparse
import csv

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser(description="extracts all patent document numbers from a JPlatPat search CSV output and puts them in BRS format")
parser.add_argument("input_file", help="JPlatPat CSV file(s) to read", nargs="*")
parser.add_argument("-v", "--version", action="version", version="%(prog)s version 2022-07-08")
args = parser.parse_args()

input_files = args.input_file
output_file = input_files[0]+".out"
pe2e_dids = set()

for input_file in input_files:
    print("Reading:", input_file)
    
    input_reader = csv.DictReader(open(input_file, encoding="utf8"))
    jplatpat_dids = set()
    for row in input_reader:
        if row['Publication number'] != '':
            jplatpat_dids.add(row['Publication number'])
        
        if row['Registration number'] != '':
            jplatpat_dids.add(row['Registration number'])
    
    for jplatpat_did in jplatpat_dids:
        
        if jplatpat_did.startswith('WO'):
            pe2e_dids.add(jplatpat_did.replace(',', '').replace('/', ''))
        else:
            assert jplatpat_did.startswith('JP')
            if '(' in jplatpat_did:
                end_year = jplatpat_did[jplatpat_did.index('(')+1:jplatpat_did.index('(')+5]
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
            
            kind_code = jplatpat_did.split(',')[-1].split('(')[0][0]
            assert kind_code.isalpha()
            
            center = jplatpat_did.split(',')[1]
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

with open(output_file, 'w') as f:
    f.write('(')
    start = True
    num_written = 0
    num_lines = 1
    for pe2e_did in pe2e_dids:
        if not(start):
            f.write(' | ')
        else:
            start = False
        f.write(pe2e_did+'$')
        num_written += 1
        
        if num_written >= 300:
            f.write(').did.')
            num_lines += 1
            num_written = 0
            start = True
            f.write('\n(')
    
    f.write(').did.')

print("Output file:", output_file)
print("Wrote out", len(pe2e_dids), "document IDs in", num_lines, "lines.")
