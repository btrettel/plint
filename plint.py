#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <https://stackoverflow.com/a/68612842>

# TODO: Check for invalid multiple dependencies.
# TODO: Check for features of other softwares.
# TODO: --reject option to write rejections to text file. Then you can delete the ones you don't want.
# TODO: Have list of common trademarks and trade names to check for. teflon, inconel. MPEP 2173.05(u).
# TODO: "Use" claim detection: method or process without word step?
# TODO: Clean up antecedent basis code.
# TODO: Check for antecedent basis issues for plural elements. Check for inconsistencies in how plural elements are referred to, for example, "two widgets" and later "the widget". (Though as-is, if I annotate the claim, it will note this problem.) ClaimMaster does the latter.

import argparse
import sys
import os
import re

# !https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def assert_warn(bool_input, message):
    global number_of_warnings
    if not bool_input:
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

def find_new_elements(claim_words, new_elements):
    capture_element = False
    element = []
    
    # find all new claim elements
    for claim_word in claim_words[1:]: # The [1:] on claim words ensures that the preamble is not captured as it will skip the first article.
        if capture_element:
            if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.'):
                claim_word_cut = claim_word[0:-1]
            else:
                claim_word_cut = claim_word
            
            if claim_word.startswith('#'):
                claim_word = claim_word[1:]
            
            if not((claim_word == 'a') or (claim_word == 'an') or (claim_word == '!') or claim_word.startswith('|')):
                element.append(claim_word_cut)
        
        # Guess where the end of the claim element is.
        if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.') or claim_word.startswith('|') or (claim_word == 'a') or (claim_word == 'an') or (claim_word == '!'):
            
            if element != []:
                new_elements.add(' '.join(element))
            
            # Stop capturing the element.
            capture_element = False
        
        if (claim_word == 'a') or (claim_word == 'an') or (claim_word == '!'):
            # Start capturing the element.
            capture_element = True
            element = []
    
    return new_elements

def find_old_elements(claim_words):
    capture_element = False
    element = []
    old_elements = set()
    
    # find all old claim elements
    for claim_word in claim_words[1:]: # The [1:] on claim words ensures that the preamble is not captured as it will skip the first article.
        if capture_element:
            if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.'):
                claim_word_cut = claim_word[0:-1]
            else:
                claim_word_cut = claim_word
            
            if claim_word.startswith('#'):
                claim_word = claim_word[1:]
            
            if not((claim_word == 'the') or (claim_word == 'said') or (claim_word == '@') or claim_word.startswith('|')):
                element.append(claim_word_cut)
        
        # Guess where the end of the claim element is.
        if claim_word.endswith(';') or claim_word.endswith(',') or claim_word.endswith(':') or claim_word.endswith('.') or claim_word.startswith('|') or (claim_word == 'the') or (claim_word == 'said') or (claim_word == '@'):
            
            if element != []:
                old_elements.add(' '.join(element))
            
            # Stop capturing the element.
            capture_element = False
        
        if (claim_word == 'the') or (claim_word == 'said') or (claim_word == '@'):
            # Start capturing the element.
            capture_element = True
            element = []
    
    return old_elements

parser = argparse.ArgumentParser(description="patent claim linter: analyses patent claims for 112(b), 112(f), and other issues")
parser.add_argument("file", help="claim file to read")
parser.add_argument("-ab", "--ant-basis", action="store_true", help="check for antecedent basis issues", default=False)
parser.add_argument("--rules", help="rules file to read",
                    default=None)
parser.add_argument("--json", action="store_true", help="use a JSON rules file (default is CSV)", default=False)
parser.add_argument('--version', action='version', version='%(prog)s version 2022-07-04')
parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS, default=False)
args = parser.parse_args()

if args.test:
    match_bool, match_str = re_matches('\\btest\\b', 'This is a test.')
    assert match_bool
    match_bool, match_str = re_matches('\\btest\\b', 'A different sentence.')
    assert not(match_bool)
    
    assert remove_punctuation('an element; another element') == 'an element another element'
    
    claim_words = "1. A contraption comprising: an enclosure |, a display |, a button |, and at least one ! widget | mounted on the enclosure, wherein the enclosure | is green, the button | is yellow, and #the at least one @ widget | is blue.".split(' ')
    
    new_elements = find_new_elements(claim_words, set())
    assert new_elements == {'enclosure', 'button', 'display', 'widget'}
    
    old_elements = find_old_elements(claim_words)
    assert old_elements == {'button', 'enclosure', 'widget'}
    
    print('All tests passed.')
    
    exit()

if args.json:
    file_ext = '.json'
    import json
else:
    file_ext = '.csv'
    import csv

if args.rules is None:
    args.rules = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rules'+file_ext)

if not args.rules.endswith(file_ext):
    eprint('Rules file must be a {} file:'.format(file_ext), args.rules)
    sys.exit(1)

if not os.path.isfile(args.file):
    eprint('Claims file does not exist:', args.file)
    sys.exit(1)

if not os.path.isfile(args.rules):
    eprint('Rules file does not exist:', args.rules)
    sys.exit(1)

if args.json:
    # Opening JSON file
    data = json.load(open(args.rules))
    rules = data['rules']
else:
    # Opening CSV file
    # Needs to be "MS-DOS" format, not UTF-8. For some reason the really old version of Python the USPTO has doesn't like Unicode CSV files.
    rules_csv = csv.DictReader(open(args.rules, 'r', encoding="ascii"))
    rules = []
    for rule in rules_csv:
        rules.append(rule)

prev_claim_number      = 0
number_of_claims       = 0
number_of_indep_claims = 0
number_of_dep_claims   = 0
number_of_warnings     = 0
claim_numbers = set()
new_elements_in_claims = {}
claims_text = []
first_claim = True

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

claims_text.append(claim_text_with_number.strip())

for claim_text_with_number in claims_text:
    number_of_claims += 1
    
    claim_number_str = claim_text_with_number.split('.', 1)[0]
    claim_text = claim_text_with_number.split('.', 1)[1].strip()
    claim_words = claim_text.lower().split(' ')
    
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
    
    for rule in rules:
        match_bool, match_str = re_matches(rule['regex'], remove_ab_notation(claim_text.lower()))
        assert_warn(not(match_bool), 'Claim {} recites "{}". {}'.format(claim_number, match_str, rule['warning'].split('#')[0].strip()))
    
    if args.ant_basis:
        # Check for antecedent basis issues.
        
        if dependent:
            new_elements = new_elements_in_claims[parent_claim]
        else:
            new_elements = set()
        new_elements = find_new_elements(claim_words, new_elements)
        
        old_elements = find_old_elements(claim_words)
        
        for old_element in old_elements:
            assert_warn(old_element in new_elements, 'Claim {} has a possible antecedent basis issue for "{}". See MPEP 2173.05(e).'.format(claim_number, old_element))
        
        new_elements_in_claims[claim_number] = new_elements
    
    prev_claim_number = claim_number

print('# of claims: {}'.format(number_of_claims))
print('Indep. claims: {}'.format(number_of_indep_claims))
print('Depen. claims: {}'.format(number_of_dep_claims))
print('Warnings: {}'.format(number_of_warnings))

assert number_of_claims == (number_of_indep_claims + number_of_dep_claims)

if number_of_warnings > 0:
    exit(2)
