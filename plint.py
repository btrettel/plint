#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import sys
import os
import re
import copy

# This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.

parser = argparse.ArgumentParser(description="patent claim linter: analyzes patent claims for 112(b), 112(d), 112(f), and other issues")
parser.add_argument("file", help="claim file to read")
parser.add_argument("-a", "--ant-basis", action="store_true", help="check for antecedent basis issues", default=False)
parser.add_argument("-d", "--debug", action="store_true", help="print debugging information", default=False)
parser.add_argument("-e", "--examiner", action="store_true", help="examiner mode: display messages relevant to USPTO patent examiners", default=False)
parser.add_argument("-f", "--filter", help="filter out warnings with this regex", nargs="*", default=[])
parser.add_argument("-o", "--outfile", action="store_true", help="output warnings to {file}.out", default=False)
parser.add_argument("-v", "--version", action="version", version="plint version 0.1.1")
parser.add_argument("-V", "--verbose", action="store_true", help="print additional information", default=False)
parser.add_argument("-w", "--warnings", help="warnings file to read", default=None)
parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS, default=False)
args = parser.parse_args()

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    if not(use_outfile):
        print(*args, file=sys.stderr, **kwargs)
    else:
        with open(outfile, 'a') as f:
            print(*args, file=f, **kwargs)

def assert_warn(bool_input, message):
    global number_of_warnings
    if not bool_input:
        if rule_filters is None:
            eprint(message)
            number_of_warnings += 1
        else:
            display_warning = True
            for rule_filter in rule_filters:
                if re.search(rule_filter, message):
                    #if not(rule_filter in message):
                    display_warning = False
            if display_warning:
                eprint(message)
                number_of_warnings += 1

def re_matches(regex, text):
    if re.search(regex, text) is None:
        return False, None
    else:
        match_str = re.search(regex, text).group()
        return True, match_str

def remove_punctuation(text):
    return text.replace(',', '').replace(';', '').replace('.', '')

def remove_ab_notation(text):
    return text.replace('{', '').replace('}', '').replace('[', '').replace(']', '').replace('#', '')

def annotate_claim_text(claim_text):
    claim_text = claim_text.lower()
    
    # Annotate plural claim element starting terms. This is hacky, but should work.
    # Note that plural claim element starting terms act differently than singular claim element starting terms like "a" or "an". For plurals, the claim element starting term itself becomes part of the claim element.
    # Other plural terms already handled as they start with a or an: a plurality, a number of
    if args.debug:
        print(claim_text)
    
    # Note: I just realized that (for example) 'two or more' would conflict with 'two'. I guess putting 'two or more' first will annotate this properly, but I haven't verified this yet.
    plural_starting_terms = {'at least one', 'one or more', 'more than one', 'two or more', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'}
    
    for plural_starting_term in plural_starting_terms:
        #print(plural_starting_term)
        
        plural_starting_term_not_annotated = True
        while plural_starting_term_not_annotated:
            # This is done iteratively because when the text is annotated, some of the starting positions change. The first iteration changes the first one that needs to be changed, the second changes the second one, etc.
            
            # Identify all instances of a plural starting term using regex to properly get the word boundaries.
            res_alls = re.finditer("\\b{}\\b".format(plural_starting_term), claim_text)
            
            # Identify all instances of a plural starting term prefixed with the, said, [, or {.
            res_dones = re.finditer("(\\bthe |\\bsaid |\[|\{)"+plural_starting_term+"\\b", claim_text)
            done_starts = set()
            if not(res_dones is None):
                for res_done in res_dones:
                    if res_done.group().startswith("the "):
                        len_to_add = 4
                    elif res_done.group().startswith("said "):
                        len_to_add = 5
                    elif res_done.group().startswith("[") or res_done.group().startswith("{"):
                        len_to_add = 1
                    else:
                        eprint("Unexpected plural starting term article:", res_done.group())
                        sys.exit(1)
                    done_starts.add(res_done.start()+len_to_add)
            
            # If the or said is not before the plural starting term, annotate the plural starting term.
            broke = False
            if not(res_alls is None):
                for res_all in res_alls:
                    if not(res_all.start() in done_starts):
                        #print(res_all.group())
                        claim_text = claim_text[0:res_all.start()]+"{"+claim_text[res_all.start():]
                        #print(claim_text)
                        broke = True
                        break
                if broke:
                    continue
            
            plural_starting_term_not_annotated = False
    
    # Annotate "a"
    claim_text = re.sub("\\ba \\b", "a {", claim_text)
    
    # Annotate "an"
    claim_text = re.sub("\\ban \\b", "an {", claim_text)
    
    # Annotate "the"
    claim_text = re.sub("\\bthe \\b", "the [", claim_text)
    
    # Annotate "said"
    claim_text = re.sub("\\bsaid \\b", "said [", claim_text)
    
    # Remove annotations for commented out terms.
    claim_text = re.sub("\#a \{", "a ", claim_text)
    claim_text = re.sub("\#an \{", "an ", claim_text)
    claim_text = re.sub("\#the \[", "the ", claim_text)
    claim_text = re.sub("\#said \[", "said ", claim_text)
    
    # Turn punctuation marks into claim element endings.
    if args.debug:
        print(claim_text)
    
    loc = 0
    curly_bracket = False
    square_bracket = False
    while loc < len(claim_text):
        char = claim_text[loc]
        
        if (char == ',') or (char == ';') or (char == ':'):
            if curly_bracket:
                claim_text = claim_text[0:loc]+"}"+claim_text[loc:]
                curly_bracket = False
                loc = loc + 1
            
            if square_bracket:
                claim_text = claim_text[0:loc]+"]"+claim_text[loc:]
                square_bracket = False
                
                loc = loc + 1
        if char == '|': # This will exclude the pipe symbol from the output.
            if curly_bracket:
                claim_text = claim_text[0:loc]+"}"+claim_text[loc+1:]
                curly_bracket = False
            
            if square_bracket:
                claim_text = claim_text[0:loc]+"]"+claim_text[loc+1:]
                square_bracket = False
        elif char == "{":
            assert not(curly_bracket), 'Curly bracket started inside of curly bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            assert not(square_bracket), 'Curly bracket started inside of square bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            curly_bracket = True
        elif char == "}":
            assert curly_bracket, 'Curly bracket ended without corresponding starting curly bracket. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            assert not(square_bracket), 'Curly bracket ended inside of square bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            curly_bracket = False
        elif char == "[":
            assert not(square_bracket), 'Square bracket started inside of square bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            assert not(curly_bracket), 'Square bracket started inside of curly bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            square_bracket = True
        elif char == "]":
            assert square_bracket, 'Square bracket ended without corresponding starting square bracket. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            assert not(curly_bracket), 'Square bracket ended inside of curly bracket. Nested claim elements not supported at the moment. At index {} with text "{}".'.format(loc, claim_text[loc-5:loc+5])
            square_bracket = False
        
        loc += 1
    
    if curly_bracket:
        claim_text = claim_text[0:loc-1]+"}"+claim_text[loc-1:]
        curly_bracket = False
    
    if square_bracket:
        claim_text = claim_text[0:loc-1]+"]"+claim_text[loc-1:]
        square_bracket = False
    
    if args.verbose:
        print(claim_text)
    
    assert claim_text.count("{") == claim_text.count("}"), "Error in annotation of new claim elements. Number of left curly brackets does not match number of right curly brackets."
    assert claim_text.count("[") == claim_text.count("]"), "Error in annotation of old claim elements. Number of left square brackets does not match number of right square brackets."
    
    return claim_text

if args.test:
    match_bool, match_str = re_matches('\\btest\\b', 'This is a test.')
    assert match_bool
    match_bool, match_str = re_matches('\\btest\\b', 'A different sentence.')
    assert not(match_bool)
    
    assert remove_punctuation('an element; another element') == 'an element another element'
    
    claim_text = "A contraption} comprising: an enclosure, a display, at least one button, and at least one widget} mounted on the enclosure, wherein the enclosure] is green, the at least one button] is yellow, and the at least one widget] is blue."
    
    # Test annotated claim.
    annotated_claim_text = annotate_claim_text(claim_text)
    
    assert annotated_claim_text == "a {contraption} comprising: an {enclosure}, a {display}, {at least one button}, and {at least one widget} mounted on the [enclosure], wherein the [enclosure] is green, the [at least one button] is yellow, and the [at least one widget] is blue."
    
    print('All tests passed.')
    
    exit()

rule_filters = args.filter

use_outfile = False

file_ext = '.csv'

if args.warnings is None:
    args.warnings = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'warnings'+file_ext)

if not args.warnings.endswith(file_ext):
    eprint('Warnings file must be a {} file:'.format(file_ext), args.warnings)
    sys.exit(1)

if not os.path.isfile(args.file):
    eprint('Claims file does not exist:', args.file)
    sys.exit(1)

if not os.path.isfile(args.warnings):
    eprint('Warnings file does not exist:', args.warnings)
    sys.exit(1)

# Opening CSV file.
# Needs to be "MS-DOS" format, not UTF-8. For some reason the really old version of Python the USPTO has doesn't like Unicode CSV files.

# Check that it only has two columns first.
with open(args.warnings, 'r', encoding="ascii") as warnings_csv_file:
    csv_reader = csv.reader(warnings_csv_file, delimiter=",")
    
    for row in csv_reader:
        assert len(row) == 2, "Warnings file has line without two columns: "+row[0]

with open(args.warnings, 'r', encoding="ascii") as warnings_csv_file:
    warnings_csv = csv.DictReader(warnings_csv_file, delimiter=",")
    warnings = []
    prev_regex = ''
    line_num = 1
    for warning in warnings_csv:
        assert warning['regex'] != prev_regex, "Duplicate regex in warnings file: {}".format(warning['regex'])
        prev_regex = warning['regex']
        warnings.append(warning)
        line_num += 1
        if args.debug:
            print(line_num, warning['regex'])
    
    print(len(warnings), "warnings loaded.")

# Set the use_outfile after checking that the file exists, otherwise, if the claims file doesn't exist, the error message will be printed to the output file.
use_outfile = args.outfile
if use_outfile:
    outfile = args.file+'.out'
    open(outfile, 'w').close()

prev_claim_number      = 0
number_of_claims       = 0
number_of_indep_claims = 0
number_of_dep_claims   = 0
number_of_warnings     = 0
claim_numbers = set()
new_elements_in_claims = {}
claims_text = []
first_claim = True
dav_keywords = set()

if args.debug:
    print("Constructing list with text of claims including number...")

with open(args.file) as claim_file:
    line = claim_file.readline()
    
    while line:
        line = line.replace('\n', '')
        
        if line != '':
            if line[0].isdigit():
                if '.' in line[0:4]:
                    # New claim starting
                    if not(first_claim):
                        claims_text.append(claim_text_with_number.strip())
                    else:
                        first_claim = False
                    
                    claim_text_with_number = line.strip()
                    
                    # Advance line
                    line = claim_file.readline()
                    continue
            
            claim_text_with_number += ' '+line.strip()
        
        # Advance line
        line = claim_file.readline()

# Add the last claim.
claims_text.append(claim_text_with_number.strip())

if args.debug:
    print("Processing the claims list...")

for claim_text_with_number in claims_text:
    number_of_claims += 1
    
    claim_number_str = claim_text_with_number.split('.', 1)[0]
    claim_text = claim_text_with_number.split('.', 1)[1].strip()
    claim_words = claim_text.split(' ')
    
    assert claim_number_str.isdigit(), 'Invalid claim number: {}'.format(claim_number_str)
    
    claim_number = int(claim_number_str)
    
    claim_numbers.add(claim_number)
    
    assert claim_number > prev_claim_number, 'Claim {} is out of order'.format(claim_number)
    
    assert_warn(claim_text.endswith('.'), 'Claim {} does not end with a period. See MPEP 608.01(m).'.format(claim_number))
    
    if not 'claim' in claim_text.lower():
        # independent claim
        dependent = False
        number_of_indep_claims += 1
        
        assert_warn(claim_text.startswith('A ') or claim_text.startswith('An '), "Independent claim {} does not start with 'A' or 'An'. This is not required but is typical. See MPEP 608.01(m) for the requirements.".format(claim_number))
    else:
        # dependent claim
        dependent = True
        number_of_dep_claims += 1
        
        assert_warn(claim_text.startswith('The '), "Dependent claim {} does not start with 'The'. This is not required but is typical. See MPEP 608.01(m) for the requirements.".format(claim_number))
        
        if 'claims' in claim_text.lower():
            assert_warn(claim_text.startswith('The '), "Claim {} is multiple dependent. Manually check validity. See MPEP 608.01(i).".format(claim_number))
        else:
            try:
                parent_claim_str = remove_punctuation(claim_words[claim_words.index('claim') + 1])
                parent_claim = int(parent_claim_str)
            except:
                eprint('Dependent claim {} has invalid parent claim number: {}'.format(claim_number, parent_claim_str))
            
            assert_warn(not(parent_claim == claim_number), "Dependent claim {} depends on itself.".format(claim_number))
            assert_warn(parent_claim in claim_numbers, "Dependent claim {} depends on non-existent claim {}.".format(claim_number, parent_claim))
    
    if args.debug:
        print("Going through warnings...")
    
    for warning in warnings:
        if not warning['regex'].startswith('#'):
            # For independent claims, skip warnings that only apply to dependent claims.
            if not(dependent):
                if ('112(d)' in warning['message']) or ('DEPONLY' in warning['message']) :
                    continue
            
            match_bool, match_str = re_matches(warning['regex'].lower(), remove_ab_notation(claim_text.lower()))
            message = 'Claim {} recites "{}". {}'.format(claim_number, match_str, warning['message'].split('#')[0].strip())
            assert_warn(not(match_bool), message)
            
            if match_bool:
                display_warning = True
                for rule_filter in rule_filters:
                    if re.search(rule_filter, message):
                        display_warning = False
                
                if display_warning and not(match_str in dav_keywords):
                    dav_keywords.add(match_str)
    
    if args.ant_basis:
        if args.debug:
            print("Checking for antecedent basis issues...")
        
        if args.verbose:
            print("Claim {} annotated: ".format(claim_number), end="")
        
        annotated_claim_text = annotate_claim_text(claim_text)
        
        new_elements = re.finditer(r"\{.*?\}", annotated_claim_text)
        old_elements = re.finditer(r"\[.*?\]", annotated_claim_text)
        
        # Import new elements from parent claims.
        if dependent:
            new_elements_dict = copy.deepcopy(new_elements_in_claims[parent_claim])
            new_elements_set = set(new_elements_dict.keys())
        else:
            new_elements_set = set()
            new_elements_dict = {}
        
        for new_element_iter in new_elements:
            new_element = new_element_iter.group()[1:-1]
            
            # Check if claim element is defined twice, for example, claim 1 introduces "a fastener" and claim 2 also introduces "a fastener", but it is unclear if claim 2 should have said "the fastener". Examples: App. nos. 16162122 and 16633492.
            message = 'Claim {} introduces "{}" more than once. Unclear if the "{}" is the same in both instances.'.format(claim_number, new_element, new_element)
            assert_warn(not(new_element in new_elements_set), message)
            
            if new_element in new_elements_set:
                display_warning = True
                for rule_filter in rule_filters:
                    if re.search(rule_filter, message):
                        display_warning = False
                
                if display_warning:
                    dav_keywords.add(new_element)
            else:
                new_elements_set.add(new_element)
                new_elements_dict[new_element] = new_element_iter.start()
        
        for old_element_iter in old_elements:
            old_element = old_element_iter.group()[1:-1]
            old_element_index = old_element_iter.start()
            
            ab_bool = False
            for new_element in new_elements_set:
                new_element_index = new_elements_dict[new_element]
                
                if old_element == new_element:
                    if new_element_index < old_element_index:
                        ab_bool = True
                        break
            
            message = 'Claim {} recites "{}", which possibly lacks antecedent basis. See MPEP 2173.05(e).'.format(claim_number, old_element)
            assert_warn(ab_bool, message)
            
            if not(ab_bool):
                display_warning = True
                for rule_filter in rule_filters:
                    if re.search(rule_filter, message):
                        display_warning = False
                
                if display_warning:
                    dav_keywords.add(old_element)
        
        new_elements_dict_zeroed = {}
        for new_element in new_elements_set:
            new_elements_dict_zeroed[new_element] = 0
        
        new_elements_in_claims[claim_number] = new_elements_dict_zeroed
    
    prev_claim_number = claim_number

dav_search_string = ''
for dav_keyword in dav_keywords:
    if ' ' in dav_keyword:
        dav_search_string += '"'+dav_keyword+'" '
    else:
        dav_search_string += dav_keyword+' '
dav_search_string = dav_search_string.strip()

if dav_search_string != '':
    eprint('DAV claims viewer search string:', dav_search_string)

print('# of claims: {}'.format(number_of_claims))
print('Indep. claims: {}'.format(number_of_indep_claims))
print('Depen. claims: {}'.format(number_of_dep_claims))
print('Warnings: {}'.format(number_of_warnings))

if args.examiner:
    if (number_of_indep_claims >= 4) and (number_of_dep_claims >= 25):
        eprint("Application has 4 or more independent claims and 25 or more total claims, and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")
    elif number_of_indep_claims >= 4:
        eprint("Application has 4 or more independent claims and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")
    elif number_of_dep_claims >= 25:
        eprint("Application has 25 or more total claims and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")

assert number_of_claims == (number_of_indep_claims + number_of_dep_claims)

if number_of_warnings > 0:
    exit(2)
