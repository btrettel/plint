#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# plint
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
import sys
import os
import re
import copy
from itertools import chain, combinations
import json

parser = argparse.ArgumentParser(description="patent claim linter: analyzes patent claims for 112(b), 112(d), 112(f), and other issues")
parser.add_argument("claims", help="claims file to read")
parser.add_argument("-a", "--ant-basis", action="store_true", help="check for antecedent basis issues", default=False)
#parser.add_argument("-A", "--abstract", help="document abstract for analysis")
parser.add_argument("-c", "--to-claim", help="stop analysis at this claim number", type=int, default=None)
parser.add_argument("-C", "--claims-warnings", help="claims warnings file to read", default=None)
parser.add_argument("-d", "--debug", action="store_true", help="print debugging information; automatically enables verbose flag", default=False)
parser.add_argument("-e", "--endings", action="store_true", help="give warnings for likely adverbs (words ending in -ly) and present participle phrases (words ending in -ing)", default=False)
parser.add_argument("-f", "--filter", help="filter out warnings with this regex", nargs="*", default=[])
parser.add_argument("-F", "--force", action="store_true", help="enable all commented out warnings", default=False)
parser.add_argument("-n", "--nitpick", action="store_true", help="equivalent to --ant-basis --restriction --endings --uspto", default=False)
parser.add_argument("-o", "--outfile", action="store_true", help="output warnings to {file}.out", default=False)
parser.add_argument("-r", "--restriction", action="store_true", help="analyze claims for restriction; automatically enables --ant-basis flag", default=False)
parser.add_argument("-s", "--spec", help="specification text file to read")
parser.add_argument("-t", "--title", help="document title for analysis")
parser.add_argument("-U", "--uspto", action="store_true", help="USPTO examiner mode: display messages relevant to USPTO patent examiners", default=False)
parser.add_argument("-v", "--version", action="version", version="plint version 0.15")
parser.add_argument("-V", "--verbose", action="store_true", help="print additional information", default=False)
parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS, default=False)
args = parser.parse_args()

# <https://stackoverflow.com/a/14981125/1124489>
def eprint(*args, **kwargs):
    if not(use_outfile):
        print(*args, file=sys.stderr, **kwargs)
    else:
        with open(outfile, 'a') as f:
            print(*args, file=f, **kwargs)

def warn(message, dav_keyword=None):
    global number_of_warnings
    global dav_keywords
    if rule_filters is None:
        eprint(message)
        number_of_warnings += 1
    else:
        display_warning = True
        for rule_filter in rule_filters:
            if re.search(rule_filter, message, flags=re.IGNORECASE):
                display_warning = False
        if display_warning:
            eprint(message)
            number_of_warnings += 1
            
            if not(dav_keyword is None) and not(dav_keyword in dav_keywords):
                dav_keywords.add(dav_keyword)

def assert_warn(bool_input, message, dav_keyword=None):
    if not bool_input:
        warn(message, dav_keyword=dav_keyword)

def re_matches(regex, text):
    if re.search(regex, text, flags=re.IGNORECASE) is None:
        return False, None
    else:
        match_str = re.search(regex, text, flags=re.IGNORECASE).group()
        return True, match_str

def remove_punctuation(text):
    return text.replace(',', '').replace(';', '').replace('.', '')

def remove_ab_notation(text):
    # Remove marking characters
    text = text.replace('{', '').replace('}', '').replace('[', '').replace(']', '').replace('#', '').replace('|', '').replace('!', '')
    
    # Remove text added for antecedent basis checking only.
    assert (text.count("`") % 2) == 0, "Unclosed '`' detected in claim marking, aborting."
    loc = 0
    print_text = True
    cleaned_text = ""
    while loc < len(text):
        if text[loc] == "`":
            print_text = not(print_text)
        elif print_text:
            cleaned_text += text[loc]
        
        loc += 1
    assert not("`" in cleaned_text), "Somehow a '`' character survived the cleaning."
    
    # Remove unnecessary spaces
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text

def mark_claim_text(claim_text):
    if args.debug:
        print("Input claim text:", claim_text)
        print("Marking plural claim element starting terms...")
    
    # Remove character that adds text to claims for the antecedent basis checker to make antecedent basis work.
    claim_text = claim_text.replace("`", "")
    
    # Mark plural claim element starting terms. This is hacky, but should work.
    # Note that plural claim element starting terms act differently than singular claim element starting terms like "a" or "an". For plurals, the claim element starting term itself becomes part of the claim element.
    # Other plural terms already handled as they start with a or an: a plurality, a number of
    
    # Note: I recognize that (for example) 'two or more' would conflict with 'two'. I guess putting 'two or more' first will mark this properly, but I haven't verified this yet.
    plural_starting_terms = {'at least one', 'one or more', 'more than one', 'two or more', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'}
    
    for plural_starting_term in plural_starting_terms:
        #print(plural_starting_term)
        
        plural_starting_term_not_marked = True
        while plural_starting_term_not_marked:
            # This is done iteratively because when the text is marked, some of the starting positions change. The first iteration changes the first one that needs to be changed, the second changes the second one, etc.
            
            # Identify all instances of a plural starting term using regex to properly get the word boundaries.
            res_alls = re.finditer("\\b{}\\b".format(plural_starting_term), claim_text, flags=re.IGNORECASE)
            
            # Identify all instances of a plural starting term prefixed with the, said, [, or {.
            res_dones = re.finditer("(\\bthe |\\bsaid |\[|\{)"+plural_starting_term+"\\b", claim_text, flags=re.IGNORECASE)
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
                        warn("Unexpected plural starting term article: {}".format(res_done.group()), dav_keyword=res_done.group())
                        sys.exit(1)
                    done_starts.add(res_done.start()+len_to_add)
            
            # If the or said is not before the plural starting term, mark the plural starting term.
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
            
            plural_starting_term_not_marked = False
    
    if args.debug:
        print("Marking singular claim element starting terms...")
    
    # Mark "a"
    claim_text = re.sub("\\bA \\b", "A {", claim_text)
    claim_text = re.sub("\\ba \\b", "a {", claim_text)
    
    # Mark "an"
    claim_text = re.sub("\\bAn \\b", "An {", claim_text)
    claim_text = re.sub("\\ban \\b", "an {", claim_text)
    
    # Mark "the"
    claim_text = re.sub("\\bThe \\b", "The [", claim_text)
    claim_text = re.sub("\\bthe \\b", "the [", claim_text)
    
    # Mark "said"
    claim_text = re.sub("\\bSaid \\b", "Said [", claim_text)
    claim_text = re.sub("\\bsaid \\b", "said [", claim_text)
    
    # Remove markings for commented out terms.
    claim_text = re.sub("\#A \{", "A ", claim_text)
    claim_text = re.sub("\#a \{", "a ", claim_text)
    claim_text = re.sub("\#An \{", "An ", claim_text)
    claim_text = re.sub("\#an \{", "an ", claim_text)
    claim_text = re.sub("\#The \[", "The ", claim_text)
    claim_text = re.sub("\#the \[", "the ", claim_text)
    claim_text = re.sub("\#Said \[", "Said ", claim_text)
    claim_text = re.sub("\#said \[", "said ", claim_text)
    
    if args.debug:
        print("Claim text after automatically marking starting terms:", claim_text)
        print("Turning punctuation marks and vertical pipes into claim element endings...")
    
    # Turn punctuation marks into claim element endings.
    
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
        if char == '!': # This will exclude the exclamation point and the character before it from the output. Then it'll got back one to capture the end of the element properly
            claim_text = claim_text[0:loc-1]+claim_text[loc+1:]
            loc -= 2 # Go back two now, will change to just one later when loc += 1 is encountered.
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
        print("Marking completed:", claim_text)
    
    assert claim_text.count("{") == claim_text.count("}"), "Error in marking of new claim elements. Number of left curly brackets does not match number of right curly brackets."
    assert claim_text.count("[") == claim_text.count("]"), "Error in marking of old claim elements. Number of left square brackets does not match number of right square brackets."
    assert not("|" in claim_text), "Error in marking of end of a claim element. Look for '|' by itself in the marked claim."
    
    return claim_text

# <https://stackoverflow.com/a/40986475>
def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)  # allows duplicate elements
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

def load_warnings_file(file_to_load):
    # Opening CSV file.
    # Needs to be "MS-DOS" format, not UTF-8. For some reason the really old version of Python the USPTO has doesn't like Unicode CSV files.

    # Check that it only has two columns first.
    with open(file_to_load, 'r', encoding="ascii") as warnings_csv_file:
        csv_reader = csv.reader(warnings_csv_file, delimiter=",")
        
        for row in csv_reader:
            assert len(row) == 2, "The warnings file should have two columns. This line does not: "+row[0]

    with open(file_to_load, 'r', encoding="ascii") as warnings_csv_file:
        warnings_csv = csv.DictReader(warnings_csv_file, delimiter=",")
        warnings = []
        prev_regex = ''
        line_num = 1
        warnings_commented_out = 0
        for warning in warnings_csv:
            if args.force:
                if warning['regex'].startswith('#'):
                    warning['regex'] = warning['regex'][1:]
            
            if not warning['regex'].startswith('#'):
                assert warning['regex'] != prev_regex, "Duplicate regex in warnings file: {}".format(warning['regex'])
                prev_regex = warning['regex']
                warnings.append(warning)
                line_num += 1
                if args.debug:
                    print("Reading from warnings file:", line_num, warning['regex'])
            else:
                warnings_commented_out += 1
        
        print("{} warnings loaded from {}, {} suppressed.\n".format(len(warnings), file_to_load, warnings_commented_out))
    
    return warnings

if args.test:
    match_bool, match_str = re_matches('\\btest\\b', 'This is a test.')
    assert match_bool
    match_bool, match_str = re_matches('\\btest\\b', 'A different sentence.')
    assert not(match_bool)
    
    assert remove_punctuation('an element; another element') == 'an element another element'
    
    claim_text = "A contraption} comprising: an enclosure, a display, at least one button, and at least one widget} mounted on the enclosure, wherein the enclosure] is green, the at least one button] is yellow, and the at least one widget] is blue."
    
    # Test marked claim.
    marked_claim_text = mark_claim_text(claim_text)
    
    assert marked_claim_text == "a {contraption} comprising: an {enclosure}, a {display}, {at least one button}, and {at least one widget} mounted on the [enclosure], wherein the [enclosure] is green, the [at least one button] is yellow, and the [at least one widget] is blue."
    
    claim_text = "This is a test. `Commented out`"
    
    cleaned_claim_text = remove_ab_notation(claim_text)
    
    assert cleaned_claim_text == "This is a test."
    
    print('All tests passed.')
    
    exit()

if args.claims.endswith('.json'):
    # Instead of using command line flags, get configuration from JSON file.
    
    json_file = copy.deepcopy(args.claims)
    
    data = json.load(open(json_file))
    
    if ('debug' in data) and not(args.debug):
        args.debug = data['debug']
    
    if args.debug:
        print("Reading configuration from JSON input file...")
    
    args.claims = None
    
    all_args = set()
    for arg in dir(args):
        if not arg.startswith("_"):
            all_args.add(arg)
    
    for key in data:
        assert key in all_args, "JSON input file has name which is not a valid command line argument: {}".format(key)
        
        if (getattr(args, key) == False) or (getattr(args, key) is None) or (getattr(args, key) == []):
            if args.debug:
                print("Setting {}: {}".format(key, data[key]))
            
            setattr(args, key, data[key])
    
    assert not(args.claims is None), "Claims file not set in JSON file."
    assert isinstance(args.filter, list), "In the JSON file, the name 'filter' must be an array."

if args.debug:
    print("Reading {}...".format(args.claims))

rule_filters = args.filter

use_outfile = False

file_ext = '.csv'

if args.nitpick:
    args.ant_basis   = True
    args.endings     = True
    args.uspto       = True
    args.restriction = True

if args.debug:
    args.verbose = True

if args.restriction:
    args.ant_basis = True

if args.claims_warnings is None:
    args.claims_warnings = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'claims'+file_ext)

if not args.claims_warnings.endswith(file_ext):
    eprint('Warnings file must be a {} file:'.format(file_ext), args.claims_warnings)
    sys.exit(1)

if not os.path.isfile(args.claims):
    eprint('Claims file does not exist:', args.claims)
    sys.exit(1)

if not os.path.isfile(args.claims_warnings):
    eprint('Warnings file does not exist:', args.claims_warnings)
    sys.exit(1)

warnings = load_warnings_file(args.claims_warnings)

# Set the use_outfile after checking that the file exists, otherwise, if the claims file doesn't exist, the error message will be printed to the output file.
use_outfile = args.outfile
if use_outfile:
    outfile = args.claims+'.out'
    open(outfile, 'w').close()

prev_claim_number      = 0
number_of_claims       = 0
number_of_indep_claims = 0
number_of_dep_claims   = 0
claim_numbers = set()
new_elements_in_claims = {}
claims_text = []
first_claim = True
shortest_indep_claim_len = 1e6
shortest_indep_claim_number_by_len = 0
indep_claims = set()
indep_claim_types = {}

# global variables
number_of_warnings = 0
dav_keywords       = set()

if not args.title is None:
    args.title = args.title.strip()
    
    title_warnings_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'title'+file_ext)
    
    title_warnings = load_warnings_file(title_warnings_file)
    
    assert_warn(len(args.title) <= 500, "The title is {} characters long. The maximum title length under 37 CFR 1.72 is 500 characters. See MPEP 606.".format(len(args.title)))
    
    for title_warning in title_warnings:
        if args.debug:
            print("Trying regex:", warning['regex'])
        
        match_bool, match_str = re_matches(title_warning['regex'], args.title)
        message = 'Title recites "{}". {}'.format(match_str, title_warning['message'].split('#')[0].strip())
        assert_warn(not(match_bool), message)

if not args.spec is None:
    # Check for lexicographic definitions.
    with open(args.spec, "r", encoding="utf-8") as spec_file:
        line = spec_file.readline()
        
        while line:
            line = line.replace('\n', '')
            
            result = re.search(r"\b(i\.e\.|, that is|meaning|means (?!for|to)|definitions?|defines?|defined|defining|terms?|terminology|phrases?)\b", line, flags=re.IGNORECASE)
            
            if not result is None:
                warn("Spec. line with possible lexicographic definition: {}".format(line))
            
            # Advance line
            line = spec_file.readline()

if args.debug:
    print("Constructing list with text of claims including number...")

with open(args.claims) as claim_file:
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
    claim_number_str = claim_text_with_number.split('.', 1)[0]
    claim_text = claim_text_with_number.split('.', 1)[1].strip()
    claim_words = claim_text.split(' ')
    cleaned_claim_text = remove_ab_notation(claim_text)
    
    assert claim_number_str.isdigit(), 'Invalid claim number: {}'.format(claim_number_str)
    
    claim_number = int(claim_number_str)
    
    if not(args.to_claim is None):
        if claim_number > args.to_claim:
            eprint("Not all claims were analyzed. Stopping at claim {}.".format(args.to_claim))
            print("Not all claims were analyzed. Stopping at claim {}.".format(args.to_claim))
            break
    
    number_of_claims += 1
    claim_numbers.add(claim_number)
    
    assert not(claim_number == prev_claim_number), 'There are multiple of claim {}.'.format(claim_number)
    
    assert claim_number > prev_claim_number, 'Claim {} is out of order'.format(claim_number)
    
    assert_warn(cleaned_claim_text.endswith('.'), 'Claim {} does not end with a period. See MPEP 608.01(m).'.format(claim_number))
    
    claim_len = len(cleaned_claim_text)
    if args.debug:
        print("Length of claim {}: {} characters.".format(claim_number, claim_len))
    
    parent_claim = None
    
    if not 'claim' in cleaned_claim_text:
        # independent claim
        dependent = False
        number_of_indep_claims += 1
        
        indep_claims.add(claim_number)
        
        assert_warn(cleaned_claim_text.startswith('A ') or cleaned_claim_text.startswith('An '), "Independent claim {} does not start with 'A' or 'An'. This is not required but is typical. See MPEP 608.01(m) for the requirements.".format(claim_number))
        
        # Keep track of which claim is shortest. This only checks independent claims since the shortest claim must be an independent claim.
        if claim_len < shortest_indep_claim_len:
            if args.debug:
                print("Independent claim {} ({}) is shorter than claim {} ({}).".format(claim_number, claim_len, shortest_indep_claim_number_by_len, shortest_indep_claim_len))
            
            shortest_indep_claim_len = claim_len
            shortest_indep_claim_number_by_len = claim_number
        
        # TODO: Support other claim types. MPEP 2106.03.
        # Determine type of claim
        if re.search("\\bmethod\\b", cleaned_claim_text) or re.search("\\bprocess\\b", cleaned_claim_text, flags=re.IGNORECASE):
            indep_claim_types[claim_number] = 'method'
        else:
            indep_claim_types[claim_number] = 'apparatus'
    else:
        # dependent claim
        dependent = True
        number_of_dep_claims += 1
        
        assert_warn(cleaned_claim_text.startswith('the '), "Dependent claim {} does not start with 'The'. This is not required but is typical. See MPEP 608.01(m) for the requirements.".format(claim_number))
        
        if 'claims' in cleaned_claim_text:
            warn("Claim {} is possibly multiple dependent. Manually check validity. See MPEP 608.01(i).".format(claim_number))
        else:
            try:
                parent_claim_str = remove_punctuation(claim_words[claim_words.index('claim') + 1])
                parent_claim = int(parent_claim_str)
            except:
                warn('Dependent claim {} possibly has invalid parent claim number: {}'.format(claim_number, parent_claim_str))
                parent_claim = None
            
            assert_warn(not(parent_claim == claim_number), "Dependent claim {} depends on itself. Potential 112(d) rejection.".format(claim_number))
            assert_warn(parent_claim < claim_number, "Dependent claim {} depends on claim {}, which is not a preceding claim. See MPEP 608.01(n).IV".format(claim_number, parent_claim))
            assert_warn(parent_claim in claim_numbers, "Dependent claim {} depends on non-existent claim {}. Potential 112(d) rejection.".format(claim_number, parent_claim))
    
    if dependent:
        assert not(parent_claim is None), "Parent claim undefined for dependent claim {}?".format(claim_number)
    
    if args.debug:
        print("Going through claim warnings...")
    
    if args.verbose:
        print("Claim {} as being checked for warnings:".format(claim_number), cleaned_claim_text)
    
    # Do some checks that will have many false positives.
    if args.endings:
        # Check for adverbs.
        # <https://medium.com/analysts-corner/six-tips-for-writing-unambiguous-requirements-70bad5422427>
        possible_adverbs_iter = re.finditer(r"\b\w*ly\b", cleaned_claim_text, flags=re.IGNORECASE)
        
        for possible_adverb_iter in possible_adverbs_iter:
            possible_adverb = possible_adverb_iter.group()
            
            # To reduce false positives, allow certain -ing words that aren't adverbs.
            if possible_adverb in {'assembly', 'supply', 'apply', 'only', 'family', 'likely', 'fly', 'imply', 'comply', 'bodily', 'multiply', 'poly', 'reply', 'rely'}:
                continue
            
            warn('Claim {} recites "{}". Possible adverb. Adverbs are frequently ambiguous.'.format(claim_number, possible_adverb), dav_keyword=possible_adverb)
        
        # Check for present participle phrases, which could indicate likely functional language.
        # <https://www.ssiplaw.com/112f-has-a-hair-trigger-avoiding-means-plus-function-misfires/>
        possible_functional_terms_iter = re.finditer(r"\b\w*ing\b", cleaned_claim_text, flags=re.IGNORECASE)
        
        for possible_functional_term_iter in possible_functional_terms_iter:
            possible_functional_term = possible_functional_term_iter.group()
            
            # To reduce false positives, allow certain -ing words that aren't functional.
            if possible_functional_term in {'comprising', 'including', 'casing'}:
                continue
            
            warn('Claim {} recites "{}". Possible functional language due to present participle wording.'.format(claim_number, possible_functional_term), dav_keyword=possible_functional_term)
    
    for warning in warnings:
        if args.debug:
            print("Trying regex:", warning['regex'])
        
        # For independent claims, skip warnings that only apply to dependent claims.
        if not(dependent):
            if ('112(d)' in warning['message']) or ('DEPONLY' in warning['message']) :
                continue
        
        match_bool, match_str = re_matches(warning['regex'], cleaned_claim_text)
        message = 'Claim {} recites "{}". {}'.format(claim_number, match_str, warning['message'].split('#')[0].strip())
        assert_warn(not(match_bool), message, dav_keyword=match_str)
    
    if args.ant_basis:
        if args.debug:
            print("Checking for antecedent basis issues...")
        
        if args.verbose:
            print("Marking claim {}...".format(claim_number))
        
        marked_claim_text = mark_claim_text(claim_text)
        
        new_elements = re.finditer(r"\{.*?\}", marked_claim_text, flags=re.IGNORECASE)
        old_elements = re.finditer(r"\[.*?\]", marked_claim_text, flags=re.IGNORECASE)
        
        # Import new elements from parent claims.
        if dependent:
            if args.debug:
                print("Importing new claim elements from claim {} for claim {}...".format(parent_claim, claim_number))
                print(new_elements_in_claims[parent_claim])
            
            new_elements_dict = {}
            for new_element in new_elements_in_claims[parent_claim]:
                new_elements_dict[new_element] = 0
            
            #new_elements_dict = copy.deepcopy(new_elements_in_claims[parent_claim])
            new_elements_set = set(new_elements_dict.keys())
        else:
            new_elements_set = set()
            new_elements_dict = {}
        
        for new_element_iter in new_elements:
            new_element = new_element_iter.group()[1:-1]
            
            # Check if claim element is defined twice, for example, claim 1 introduces "a fastener" and claim 2 also introduces "a fastener", but it is unclear if claim 2 should have said "the fastener". Examples: App. nos. 16162122 and 16633492.
            message = 'Claim {} introduces "{}" more than once. Unclear if the "{}" is the same in both instances.'.format(claim_number, new_element, new_element)
            assert_warn(not(new_element in new_elements_set), message, dav_keyword=new_element)
            
            if not(new_element in new_elements_set):
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
            assert_warn(ab_bool, message, dav_keyword=old_element)
        
        new_elements_in_claims[claim_number] = new_elements_dict
    
    prev_claim_number = claim_number

if args.debug and args.ant_basis:
    for claim_number in claim_numbers:
        print("New elements in claim {}:".format(claim_number), new_elements_in_claims[claim_number])

if args.spec and args.ant_basis:
    all_elements = set()
    for claim_number in claim_numbers:
        for element in new_elements_in_claims[claim_number]:
            #print(claim_number, element)
            all_elements.add(element)
    
    spec_appearances_of_element = {}
    for element in all_elements:
        spec_appearances_of_element[element] = 0
    
    with open(args.spec, "r", encoding="utf-8") as spec_file:
        line = spec_file.readline()
        
        while line:
            line = line.replace('\n', '')
            
            for element in all_elements:
                if element in line:
                    spec_appearances_of_element[element] += line.count(element)
            
            # Advance line
            line = spec_file.readline()
    
    for element in spec_appearances_of_element:
        if spec_appearances_of_element[element] == 0:
            warn("Claim element that does not appear in the spec: {}. Possible drawing objection if element not in drawing. See MPEP 608.02(d). Possible weak disclosure for element, leading to 112(a) issues.".format(element), dav_keyword=element)
        elif spec_appearances_of_element[element] <= 2:
            warn("Claim element that appears in the spec 2 or fewer times: {}. Possible weak disclosure for element, leading to 112(a) issues.".format(element), dav_keyword=element)

assert_warn(shortest_indep_claim_number_by_len == 1, "The least restrictive claim (by number of characters) is claim {}. However, claim 1 is supposed to be the least restrictive claim. Check that it is. See MPEP 608.01(i).".format(claim_number))

if args.ant_basis:
    shortest_indep_claim_elements = 1e6
    shortest_indep_claim_number_by_elements = 0
    for claim_number in claim_numbers:
        number_of_elements = len(new_elements_in_claims[claim_number])
        
        if number_of_elements < shortest_indep_claim_elements:
            shortest_indep_claim_number_by_elements = claim_number
            shortest_indep_claim_elements = number_of_elements
    
    assert_warn(shortest_indep_claim_number_by_elements == 1, "The least restrictive claim (by number of claim elements) is claim {}. However, claim 1 is supposed to be the least restrictive claim. Check that it is. See MPEP 608.01(i).".format(claim_number))

dav_search_string = ''
for dav_keyword in dav_keywords:
    if ' ' in dav_keyword:
        dav_search_string += '"'+dav_keyword+'" '
    else:
        dav_search_string += dav_keyword+' '
dav_search_string = dav_search_string.strip()

if dav_search_string != "":
    eprint("\nDAV claims viewer search string:", dav_search_string)

if args.restriction:
    if not args.spec is None:
        eprint('\nSpecies election analysis (see MPEP 806.04):\n')
        
        # Check for phrases in the spec that could indicate a species election is possible. For now this checks if certain text appears in the "BRIEF DESCRIPTION OF THE DRAWINGS" section or a similarly titled section.
        
        no_possible_species_elections_detected = True
        
        with open(args.spec, "r", encoding="utf-8") as spec_file:
            line = spec_file.readline()
            
            in_drawings_section = False
            
            while line:
                line = line.replace('\n', '').strip()
                
                if line.isupper():
                    if args.debug:
                        print("New section:", line)
                    
                    if re.search(r"\b(DRAWINGS|FIGURES)\b", line):
                        in_drawings_section = True
                        if args.debug:
                            print("Drawings section detected.")
                    else:
                        in_drawings_section = False
                
                # - US20200030830A1: > FIG. 3A shows the same perspective view of the lower valve member without the upstream flow restriction fingers.
                #   - number followed by letter could indicate an alternative embodiment?
                # - `^(fig\.|figure) \d.*\b(alternative|alternate|another|further|optional)\b^`
                #   - US20200298253A1, US20190321835A1, US20200301454A1, US20210170426A1, US20200238317A1, US20200129996A1, US20200068820A1 (fig. 8)
                #   - also: yet another
                # - `^(fig\.|figure) \d.*\b(second|third|fourth|fifth|sixth) embodiment\b`
                #   - US20210031223A1, US20170120285A1
                # - Species election based on paragraphs of specification:
                #   - US20200238317A1
                # - Unclear how to handle: US20200246764A1, US20210387211A1, US20200282410A1, US20200068820A1, US20220048367A1
                
                if in_drawings_section:
                    if args.debug:
                        print("In drawings section:", line)
                    if re.search(r"^(fig\.|figure) \d.*\b(alternative|alternate|another|further|optional)\b^", line, flags=re.IGNORECASE) or re.search(r"^(fig\.|figure) \d.*\b(second|third|fourth|fifth|sixth) embodiment\b", line, flags=re.IGNORECASE):
                        warn("Possible species election: {}".format(line))
                        no_possible_species_elections_detected = False
                
                # Advance line
                line = spec_file.readline()
        
        if no_possible_species_elections_detected:
            eprint("No possible species elections detected. These can usually be found by looking at the figures.")
    
    if len(indep_claims) > 1:
        eprint('\n"Catalog of parts" restriction analysis:\n')
        # I'm calling it the "catalog of parts" restriction analysis as it only looks at identified claim elements and not their functions or how the parts are connected or related. This terminology is used by the following:
        # <https://www.djstein.com/IP/Files/Landis%20on%20Mechanics%20of%20Patent%20Claim%20Drafting.pdf>
        # <https://repository.law.uic.edu/ripl/vol13/iss1/2/>
        # <https://scholarlycommons.law.emory.edu/elj/vol65/iss4/2>
        possible_restriction = False
        for i, claim_combo in enumerate(powerset(indep_claims), 1):
            if len(claim_combo) == 2:
                claim_list = list(claim_combo)
                #print("Claim combination being analyzed for restrictions: {}".format(claim_list))
                
                claim_X = claim_list[0]
                claim_Y = claim_list[1]
                
                claim_X_elements = set(new_elements_in_claims[claim_X].keys())
                claim_Y_elements = set(new_elements_in_claims[claim_Y].keys())
                
                common_elements = set()
                claim_X_unique_elements = copy.deepcopy(claim_X_elements)
                claim_Y_unique_elements = copy.deepcopy(claim_Y_elements)
                
                for claim_X_element in claim_X_elements:
                    if claim_X_element in claim_Y_unique_elements:
                        claim_Y_unique_elements.remove(claim_X_element)
                        common_elements.add(claim_X_element)
                
                for claim_Y_element in claim_Y_elements:
                    if claim_Y_element in claim_X_unique_elements:
                        claim_X_unique_elements.remove(claim_Y_element)
                
                eprint("Category of claim {}: {}".format(claim_X, indep_claim_types[claim_X]))
                eprint("Category of claim {}: {}".format(claim_Y, indep_claim_types[claim_Y]))
                eprint("Elements common to claims {} and {}: {}".format(claim_X, claim_Y, common_elements))
                eprint("Elements unique to claim {}: {}".format(claim_X, claim_X_unique_elements))
                eprint("Elements unique to claim {}: {}".format(claim_Y, claim_Y_unique_elements))
                
                if len(common_elements) == 0:
                    warn("Possible restriction. Claims {} and {} may be unrelated/independent. See MPEP 806.06. Check for dependent linking claims.".format(claim_X, claim_Y))
                    possible_restriction = True
                
                # Situations considered here:
                # 
                # ABbr = claim X
                # Bsp = claim Y
                # A = claim_X_unique_elements
                # Bbr = common_elements
                # Bsp - Bbr = claim_Y_unique_elements
                # 
                # or
                # 
                # ABbr = claim Y
                # Bsp = claim X
                # A = claim_Y_unique_elements
                # Bbr = common_elements
                # Bsp - Bbr = claim_X_unique_elements
                # 
                # All that needs to be shown is that there are common elements (Bbr), and there are extra elements corresponding to A and Bsp - Br in claims X and Y. Which claims correspond to A and Bsp does not matter.
                if (len(claim_X_unique_elements) > 0) and (len(claim_Y_unique_elements) > 0) and (len(common_elements) > 0) and (indep_claim_types[claim_X] == indep_claim_types[claim_Y]):
                    warn("Possible restriction. {} claims {} and {} may be related as combination-subcombination. See MPEP 806.05(c). Check for dependent linking claims.".format(indep_claim_types[claim_X].capitalize(), claim_X, claim_Y))
                    possible_restriction = True
                
                # Though the `(len(claim_X_unique_elements) > 0) or (len(claim_Y_unique_elements) > 0)` part is not necessarily required, without it, this is likely to return many false positives. Process claims which merely repeat the product claim are not likely to be restrictable, so the extra condition in the first sentence is practically necessary
                if (((indep_claim_types[claim_X] == 'method') and (indep_claim_types[claim_Y] == 'apparatus')) or ((indep_claim_types[claim_X] == 'apparatus') and (indep_claim_types[claim_Y] == 'method'))) and (len(common_elements) > 0) and ((len(claim_X_unique_elements) > 0) or (len(claim_Y_unique_elements) > 0)):
                    warn("Possible restriction. {} claim {} and {} claim {} may be related as a distinct product and process pair. See MPEP 806.05(e)-806.05(i). Check for dependent linking claims.".format(indep_claim_types[claim_X].capitalize(), indep_claim_types[claim_Y], claim_X, claim_Y))
                    possible_restriction = True
                
                eprint()
        
        if not(possible_restriction):
            warn("No restriction appears possible on the basis of claim elements alone. Relationships between the elements or functions of the elements might allow a restriction. A species election may be possible as well.\n")
    else:
        warn("\nOnly one independent claim. A species election may be possible.")

if args.uspto:
    if (number_of_indep_claims >= 4) and (number_of_dep_claims >= 25):
        warn("Application has 4 or more independent claims and 25 or more total claims, and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")
    elif number_of_indep_claims >= 4:
        warn("Application has 4 or more independent claims and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")
    elif number_of_dep_claims >= 25:
        warn("Application has 25 or more total claims and consequently is eligible for 1 hour of attribute time. See Examiner PAP, Oct. 2021.")

print()
print("Summary statistics:")
print("# of claims: {}".format(number_of_claims))
print("Indep. claims: {}".format(number_of_indep_claims), indep_claim_types)
print("Depen. claims: {}".format(number_of_dep_claims))
print("Warnings: {}".format(number_of_warnings))

assert(number_of_indep_claims == len(indep_claims))

assert number_of_claims == (number_of_indep_claims + number_of_dep_claims)

if number_of_warnings > 0:
    exit(2)
