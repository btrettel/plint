#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv

# This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = argparse.ArgumentParser(description="lists top JPFI classifications in JPlatPat CSV files")
parser.add_argument("input_file", help="JPlatPat CSV file(s) to read", nargs="*")
parser.add_argument("-v", "--version", action="version", version="%(prog)s version 2022-07-08")
args = parser.parse_args()

input_files = args.input_file
FI_dict = {}
IPC_dict = {}

for input_file in input_files:
    print("Reading:", input_file)
    
    input_reader = csv.DictReader(open(input_file, encoding="utf8"))
    for row in input_reader:
        row_FIs = set()
        row_IPCs = set()
        for component in row['FI'].split(","):
            if component[0].isalpha(): # Start of section.
                FI = component
                row_IPCs.add(component)
            elif component[0].isdigit(): # Start of expansion code.
                FI += ','+component
                row_FIs.add(FI)
            else:
                eprint("Invalid FI component:", component)
                exit(1)
        
        for FI in row_FIs:
            if FI in FI_dict.keys():
                FI_dict[FI] += 1
            else:
                FI_dict[FI] = 1
        
        for IPC in row_IPCs:
            if IPC in IPC_dict.keys():
                IPC_dict[IPC] += 1
            else:
                IPC_dict[IPC] = 1

# <https://stackoverflow.com/a/3177911>
print("Top JPFIs:")
for w in sorted(FI_dict, key=FI_dict.get, reverse=True):
    print(w, FI_dict[w])

print("\nTop IPCs:")
for w in sorted(IPC_dict, key=IPC_dict.get, reverse=True):
    print(w, IPC_dict[w])
