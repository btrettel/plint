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
parser.add_argument("-f", "--filter", help="filter out warnings with this regex", nargs="*", default=[])
parser.add_argument("-o", "--outfile", action="store_true", help="output warnings to {file}.out", default=False)
parser.add_argument("-v", "--version", action="version", version="plint version 2022-07-08")
parser.add_argument("-w", "--warnings", help="warnings file to read", default=None)
parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS, default=False)
args = parser.parse_args()

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    if not(outfile_bool):
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
    return text.replace(' |', '').replace('! ', '').replace('@ ', '')

def find_new_elements(claim_words, new_elements_copy, claim_number):
    new_elements = copy.deepcopy(new_elements_copy) # Needed to prevent the list of claim elements from including claim elements not in the dependency tree due to Python's shallow copying.
    capture_element = False
    element = []
    
    # find all new claim elements
    for claim_word in claim_words:
        if capture_element:
            if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.'):
                claim_word_cut = claim_word[0:-1]
            else:
                claim_word_cut = claim_word
            
            if claim_word.startswith('#'):
                claim_word = claim_word[1:]
            
            if not((claim_word == '!') or (claim_word == '@') or claim_word.startswith('|')):
                element.append(claim_word_cut)
        
        # Guess where the end of the claim element is.
        if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.') or claim_word.startswith('|') or (claim_word == '!') or (claim_word == '@'):
            if element != []:
                element_str = ' '.join(element)
                
                # Check if claim element is defined twice, for example, claim 1 introduces "a fastener" and claim 2 also introduces "a fastener", but it is unclear if claim 2 should have said "the fastener". Examples: App. nos. 16162122 and 16633492.
                message = 'Claim {} introduces "{}" more than once.'.format(claim_number, element_str)
                assert_warn(not(element_str in new_elements), message)
                
                if element_str in new_elements:
                    display_warning = True
                    for rule_filter in rule_filters:
                        if re.search(rule_filter, message):
                            display_warning = False
                    
                    if display_warning and not(element_str in dav_keywords):
                        dav_keywords.add(element_str)
                
                new_elements.add(element_str)
                element = []
            
            # Stop capturing the element.
            capture_element = False
        
        if (claim_word == 'a') or (claim_word == 'an') or (claim_word == '!'):
            # Start capturing the element.
            capture_element = True
            
            # Note that unlike earlier versions of plint, this will continue capturing if it was already capturing. So, for example, "a center of a widget" will return a single element, not "a center of a widget" and "a widget".
            # TODO: Run find_new_elements() on the returned element to get the "sub-element". Use "\" to split up sub-elements. Some old elements could be found too, which would require making this function output old elements too. Or is that not the case? The old elements are found in a different pass, so they should still be found.
    
    return new_elements

def find_old_elements(claim_words):
    capture_element = False
    element = []
    old_elements = set()
    
    # find all old claim elements
    for claim_word in claim_words:
        if capture_element:
            if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.'):
                claim_word_cut = claim_word[0:-1]
            else:
                claim_word_cut = claim_word
            
            if claim_word.startswith('#'):
                claim_word = claim_word[1:]
            
            if not((claim_word == '!') or (claim_word == '@') or claim_word.startswith('|')):
                element.append(claim_word_cut)
        
        # Guess where the end of the claim element is.
        if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.') or claim_word.startswith('|') or (claim_word == '!') or (claim_word == '@'):
            
            if element != []:
                old_elements.add(' '.join(element))
                element = []
            
            # Stop capturing the element.
            capture_element = False
        
        if (claim_word == 'the') or (claim_word == 'said') or (claim_word == '@'):
            # Start capturing the element.
            capture_element = True
            
            # Note that unlike earlier versions of plint, this will continue capturing if it was already capturing. So, for example, "the center of the widget" will return a single element, not "the center of the widget" and "the widget".
            # TODO: Run find_old_elements() on the returned element to get the "sub-element". Use "\" to split up sub-elements. Some new elements could be found too, which would require making this function output new elements too. Or is that not the case? The new elements are found in a different pass, so they should still be found.
    
    return old_elements

def extract_claim_words_and_annotate(claim_text):
    # Annotate plural claim element starting terms. This is hacky, but should work.
    # Note that plural claim element starting terms act differently than singular claim element starting terms like "a" or "an". For plurals, the claim element starting term itself becomes part of the claim element. So if I switch to annotating "a" and "an" in this part of the code, then I'd have to have a different section to add the ' ! ' *after* the starting term, in contrast to *before* as done below.
    # Other plural terms already handled as they start with a or an: a plurality, a number of
    plural_starting_terms = {'at least one', 'one or more', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'}
    
    for plural_starting_term in plural_starting_terms:
        # Simpler regex version of this code:
        # match: "\b(the|said) "+plural_starting_term+"\b"
        # replacement: 
        
        # Replace old claim element starting terms temporarily to make next replacement work right.
        claim_text = claim_text.replace('the '+plural_starting_term, ' %'+plural_starting_term)
        # TODO: This will work for terms that start with the. Make it work for terms that start with said too.
        
        # Annotate new claim element starting terms.
        claim_text = claim_text.replace(' '+plural_starting_term, ' ! '+plural_starting_term)
        
        # Reverse replacement for old claim element starting terms.
        claim_text = claim_text.replace(' %'+plural_starting_term, 'the '+plural_starting_term)
    
    # Finally, extract the claim words.
    claim_words = claim_text.lower().split(' ')
    
    return claim_words

if args.test:
    match_bool, match_str = re_matches('\\btest\\b', 'This is a test.')
    assert match_bool
    match_bool, match_str = re_matches('\\btest\\b', 'A different sentence.')
    assert not(match_bool)
    
    assert remove_punctuation('an element; another element') == 'an element another element'
    
    claim_text = "A contraption | comprising: an enclosure |, a display, a button, and at least one widget | mounted on the enclosure, wherein the enclosure | is green, the button | is yellow, and the at least one widget | is blue."
    claim_words = extract_claim_words_and_annotate(claim_text)
    
    assert claim_words == ['a', 'contraption', '|', 'comprising:', 'an', 'enclosure', '|,', 'a', 'display,', 'a', 'button,', 'and', '!', 'at', 'least', 'one', 'widget', '|', 'mounted', 'on', 'the', 'enclosure,', 'wherein', 'the', 'enclosure', '|', 'is', 'green,', 'the', 'button', '|', 'is', 'yellow,', 'and', 'the', 'at', 'least', 'one', 'widget', '|', 'is', 'blue.']
    
    new_elements = find_new_elements(claim_words, set(), 1)
    
    assert new_elements == {'enclosure', 'button', 'display', 'at least one widget', 'contraption'}
    
    old_elements = find_old_elements(claim_words)
    assert old_elements == {'button', 'enclosure', 'at least one widget'}
    
    print('All tests passed.')
    
    exit()

rule_filters = args.filter

outfile_bool = args.outfile
if outfile_bool:
    outfile = args.file+'.out'
    open(outfile, 'w').close()

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

# Construct list with text of claims including number.
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

for claim_text_with_number in claims_text:
    number_of_claims += 1
    
    claim_number_str = claim_text_with_number.split('.', 1)[0]
    claim_text = claim_text_with_number.split('.', 1)[1].strip()
    claim_words = extract_claim_words_and_annotate(claim_text)
    
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
            
            assert_warn(parent_claim in claim_numbers, "Dependent claim {} depends on non-existent claim {}.".format(claim_number, parent_claim))
    
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
        # Check for antecedent basis issues.
        
        if dependent:
            new_elements = new_elements_in_claims[parent_claim]
        else:
            new_elements = set()
        new_elements = find_new_elements(claim_words, new_elements, claim_number)
        
        old_elements = find_old_elements(claim_words)
        
        for old_element in old_elements:
            message = 'Claim {} has a possible antecedent basis issue for "{}". See MPEP 2173.05(e).'.format(claim_number, old_element)
            assert_warn(old_element in new_elements, message)
            
            if not(old_element in new_elements):
                display_warning = True
                for rule_filter in rule_filters:
                    if re.search(rule_filter, message):
                        display_warning = False
                
                if display_warning and not(old_element in dav_keywords):
                    dav_keywords.add(old_element)
        
        new_elements_in_claims[claim_number] = new_elements
    
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

assert number_of_claims == (number_of_indep_claims + number_of_dep_claims)

if number_of_warnings > 0:
    exit(2)
