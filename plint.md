# plint.py: Patent Claim Linter

## Usage

### Windows

On my USPTO computer (Windows), after adding `C:\Python32` and the folder where plint.py is to my path, I can run the script as follows:

    python.exe plint.py .\claims.txt

You can edit your path by using the start search button. Search for env and click on "Edit environment variables for your account". Separate the different folder paths with a semi-colon. [See here](https://answers.microsoft.com/en-us/windows/forum/all/adding-path-variable/97300613-20cb-4d85-8d0e-cc9d3549ba23) for some screenshots of the environmental variables dialog box.

If you want to run the script directly instead of through Python, you can add ;.PY to the end of the user environmental variable PATHEXT. For me, this means that I added PATHEXT in the "Edit environment variables for your account" dialog as follows:

    .COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL;.PY

Then I can run plint.py as follows:

    plint.py .\claims.txt

### Linux

On Linux, the plint.py script can be run from the directory it is in as follows:

    ./plint.py claims.txt

claims.txt is the file you wish to read, which is plain text containing the patent document claims. Each claim is numbered with a period after the number, for example: "1."

Alternatively, you can add the directory plint.py is in to your PATH and then run plint.py as follows:

    plint.py claims.txt

## Hard-coded checks

The following hard-coded checks are made:

- A check that the claim number is formatted with a period after the number, for example: "1."
- A check that the claim number is an integer.
- A check that the claims are in numerical order.
- A check that the claim ends with a period. See MPEP 608.01(m)
- A check that each independent claim starts with 'A' or 'An'. This is not required but is typical. See MPEP 608.01(m) for the requirements.
- A check that each dependent claim starts with 'The'. This is not required but is typical. See MPEP 608.01(m) for the requirements.
- A check for multiple dependent claims to manually check.
- A check that dependent claims refer back to existing claims.

## Rules file

A rules file is used to identify possibly problematic claim language.

The standard rules file ([rules.csv](rules.csv)) can be modified to add or remove rules as desired by the user. The format of this file is as follows: The first column is "regex", which contains regular expressions to match against the claims. The second column is "warning", which lists the warning displayed when the regex is matched. The file must start with a line listing the columns as "regex" and "warning".

As an example, consider the following rule:

    \belement\b,Possible 112(f) invocation. See MPEP 2181.

The `\b` code means *word boundary* in regular expressions, so this rule will match the word *element* but not match *elemental*. After the comma is the message displayed, including a convenient MPEP reference useful to determine whether claim language caught by this rule meets 112(f).

An external rules file can be called with the `--rules` flag.

The `--json` flag allows a similarly structured JSON rules file to be read instead of the standard CSV file.

Rules can be disabled in a rules file without being deleted by adding "#" to the beginning of the regex column of a rule. Comments can be added in the warning column; all text after "#" will not be printed in plint.py.

Rules with warning text containing the terms "112(d)" or "DEPONLY" will only apply to dependent claims. This is true even if "DEPONLY" is only printed in a comment.

## Filtering out warnings

Warnings can be disabled from the command line by filtering out any part of the warning message printed using the `--filter` flag followed by one or more regular expressions. For example, to filter out all rules containing the text "112(f)":

    plint.py claims.txt --filter "112\(f\)"

Then no warnings where the text contains "112(f)" will be printed. (The quotes are necessary to prevent the shell from interpreting the parentheses. And the parentheses are escaped as parentheses have a special function in regular expressions.) Multiple filters can be applied as well:

    plint.py claims.txt --filter "112\(f\)" antecedent

(As can be seen, no quotes or parentheses are necessary for single words without any special characters like "antecedent". However, multiple words will require quotes, for example: "antecedent basis" should be quoted.)

The filtering applies to both hard-coded checks and rules from a rules file.

## Antecedent basis checking

Checking for antecedent basis issues requires using the optional flag `-ab` or `--ant-basis`. This is optional because the feature requires the claims file to use a special syntax as it is difficult to automatically recognize the start and end of claim elements. plint.py will recognize that the terms "a", "an", "at least one", and "one or more" will appear before new claim elements and that the words "the" or "said" will appear before claim elements previously introduced. plint.py will also know that a claim element ends when a semi-colon, period, comma, colon, "a", or "an" appear.

To check the demo claims on Linux:

    ./plint.py -ab demo-claims.txt

The special syntax for antecedent basis issues is as follows: When the start of a new element is not detected, add the word "!" before the element. When the start of an element previously introduced is not detected, add the word "@" before the element. When the end of an element is not detected, add the word "|" after the element. When an article should not create an element, add "#" to the beginning of that word. See [demo-claims.txt](demo-claims.txt) below for this notation in use.

    1. A contraption comprising:
    an enclosure |,
    a display |,
    a button |, and
    at least one widget | mounted on the enclosure,
    wherein the enclosure | is green,
    the button | is yellow, and
    the at least one widget | is blue.

If a specific claim element is introduced more than once, a warning will be printed. For example, the following claim will produce a warning:

    1. A device comprising:
    a widget;
    a widget.

## DAV claims viewer search string

If any warnings are printed, plint.py will display a string which can be pasted into the DAV claims viewer to highlight the terms found to have issues in the claims.

## Exit statuses

- 0 means the claims pass all tests.
- 1 means that a fatal error occurred in the parsing of the claims. Typically the claims will be written in a way that violates plint.py's expectations for how a claim will be structured.
- 2 means that one or more warnings were made.
