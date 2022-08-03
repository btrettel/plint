# plint: patent claim analyzer/linter

Current version: 0.17.0

plint can analyze a text file containing patent claims for the following:

- 112(b) issues, including:
    - [antecedent basis](#antecedent-basis-checking)
    - relative terms
    - subjective terms
    - exemplary claim limitations
    - ambiguous claim limitations
    - terms of art which may be indefinite (focused on mechanical inventions)
- 112(d) issues, including:
    - [whether dependent claims refer to valid claims](#hard-coded-checks)
    - some instances where a dependent claim does not further limit its parent claim
- functional claim limitations, including 112(f)
- non-standard transitional phrases
- possibly overly narrow claim limitations
- [support for claim terms in the specification](#specification-checking)
- [restrictions](#restriction-checking)
- [claim formalities](#hard-coded-checks)

By default, plint will emulate a nitpicky examiner. When making the default claims warning file (claims.csv), before adding a line related to patent prosecution, I ask whether 1% or more of examiners or judges would reject a claim based on the presence of a particular word or phrase. I don't ask whether the rejection would be valid. claims.csv is meant to be conservative in that it will have far more warnings than rejections I would actually make. It represents rejections (valid or not) that an applicant might possibly face. If this is too nitpicky for your tastes, you're welcome to make your own warnings file or modify the existing file. plint is highly customizable.

plint is designed to run on the ancient version of Python the USPTO has on their computers, so plint won't use the latest features of Python. And the USPTO Python version is limited to the standard library, so NLTK can not be used.

## Legal

This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.

plint is licensed under the GNU Affero General Public License v3.0.

## Usage

First, keep in mind MPEP 2173.02.II:

> Examiners should note that Office policy is not to employ *per se* rules to make technical rejections. Examples of claim language which have been held to be indefinite set forth in MPEP 2173.05(d) are fact specific and should not be applied as *per se* rules.

Warnings produced by plint are *possible* rejections or objections. Each should be carefully checked as many warnings will not be valid rejections or objections. As stated above, by default plint is nitpicky, so likely most of the warnings will not be valid rejections or objections.

### Windows

On my USPTO computer (Windows), after adding `C:\Python32` and the folder where plint.py is to my path, I can run the script as follows:

    python.exe plint.py .\claims.txt

You can edit your path by using the start search button. Search for env and click on "Edit environment variables for your account". Separate the different folder paths with a semi-colon. [See here](https://answers.microsoft.com/en-us/windows/forum/all/adding-path-variable/97300613-20cb-4d85-8d0e-cc9d3549ba23) for some screenshots of the environmental variables dialog box.

If you want to run the script directly instead of through Python, you can add ;.PY to the end of the user environmental variable PATHEXT. For me, this means that I added PATHEXT in the "Edit environment variables for your account" dialog as follows:

    .COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL;.PY

Then I can run plint as follows:

    plint .\claims.txt

### Linux

On Linux, the plint script can be run from the directory it is in as follows:

    ./plint.py claims.txt

claims.txt is the file you wish to read, which is plain text containing the patent document claims. Each claim is numbered with a period after the number, for example: "1."

Alternatively, you can add the directory plint.py is in to your PATH and then run plint as follows:

    plint.py claims.txt

### How I use plint

When examining patents, I typically save the patent claims to a file named {application number}-claims.txt. For example, for application number 16811358, I will save 16811358-claims.txt. I then mark the claims for the antecedent basis checker as described below. This will require some iteration to get right, so I will run plint as follows, modify the claim marking in response to the warnings and parsing errors displayed, and repeat until plint parses the entire claim set:

    plint --ant-basis --debug --uspto --endings .\16811358-claims.txt

As discussed above, `-d` is debug mode, which will enable verbose mode as well. Debug and verbose modes display more information, and this extra information may be useful when iteratively marking the claims.

Once I am confident that I marked the claim for antecedent basis properly, I will remove the `-d` flag and add `-o` to save the output to a file:

    plint -a -o .\16811358-claims.txt

Then I will check each line in 16811358-claims.txt. Most of the warnings will not lead to rejections or objections, but all should be checked. After reading the warnings, I may decide to mark the claim differently if plint is still not interpreting the claim properly.

## Hard-coded checks

The following hard-coded checks are made:

- A check that the claim number is formatted with a period after the number, for example: "1."
- A check that the claim number is an integer.
- A check that the claims are in numerical order.
- A check that the claim ends with a period. See MPEP 608.01(m)
- A check that each independent claim starts with 'A' or 'An'. This is not required but is typical. See MPEP 608.01(m) for the requirements.
- A check that each dependent claim starts with 'The'. This is not required but is typical. See MPEP 608.01(m) for the requirements.
- A check for multiple dependent claims to manually check.
- A check that dependent claims do not refer back to themselves.
- A check that dependent claims refer back to existing claims.
- A check that claim 1 is the shortest claim as a spot check for 37 CFR 1.75(g) compliance. See MPEP 608.01(i).

## Warnings file

A warnings file is used to identify possibly problematic claim language.

The standard warnings file ([claims.csv](claims.csv)) can be modified to add or remove warnings as desired by the user. The format of this file is as follows: The first column is "regex", which contains regular expressions to match against the claims. The second column is "message", which lists the message displayed when the regex is matched. The file must start with a line listing the columns as "regex" and "message".

As an example, consider the following line:

    \belement\b,Possible 112(f) invocation. See MPEP 2181.

The `\b` code means *word boundary* in regular expressions, so this line will match the word *element* but not match *elemental*. After the comma is the message displayed, including a convenient MPEP reference useful to determine whether claim language caught by this line meets 112(f).

An external warnings file can be called with the `--warnings` flag.

Specific warnings can be disabled in a warnings file without the line being deleted by adding "#" to the beginning of the regex column of a warning. Comments can be added in the warning column; all text after "#" will not be printed in plint.

Warnings with warning text containing the terms "112(d)" or "DEPONLY" will only apply to dependent claims. This is true even if "DEPONLY" is only printed in a comment.

### Filtering out warnings

Warnings can be disabled from the command line by filtering out any part of the warning message printed using the `--filter` flag followed by one or more regular expressions. For example, to filter out all warnings containing the text "112(f)":

    plint claims.txt --filter "112\(f\)"

Then no warnings where the text contains "112(f)" will be printed. (The quotes are necessary to prevent the shell from interpreting the parentheses. And the parentheses are escaped as parentheses have a special function in regular expressions.) Multiple filters can be applied as well:

    plint claims.txt --filter "112\(f\)" antecedent

(As can be seen, no quotes or parentheses are necessary for single words without any special characters like "antecedent". However, multiple words will require quotes, for example: "antecedent basis" should be quoted.)

The filtering applies to all warnings, not just warnings from a warnings file.

### Forced mode

Commented out warnings can be forcibly reenabled from the command line with the `-F` or `--force` flag. The user can see whether any warnings are commented out from the command line output. For example, the following shows that 5 warnings are commented out:

    410 claim warnings loaded, 5 suppressed.

When plint is run with the `--force` flag, none of the warnings will be suppressed:

    415 claim warnings loaded, 0 suppressed.

## Antecedent basis checking

Checking for antecedent basis issues requires using the optional flag `-a` or `--ant-basis`. This is optional because the feature requires the claims file to use a special syntax as it is difficult to automatically recognize the start and end of claim elements. plint will recognize that the terms "a", "an", "at least one", and "one or more" will appear before new claim elements and that the words "the" or "said" will appear before claim elements previously introduced. plint will also know that a claim element ends when a semi-colon, comma, or colon appear, and at the end of a claim.

To check the demo claims on Linux:

    ./plint.py -a demo-claims.txt

The antecedent basis checker will make sure that all "old" elements were introduced earlier in the claim, or in one of the claims the current claim depends on.

If a specific claim element is introduced more than once, a warning will be printed. For example, the following claim will produce a warning:

    1. A device comprising:
    a widget;
    a widget.

### Special syntax for antecedent basis analysis

- When the start of a new element is not detected, add `{` before the element.
- When the start of an element previously introduced is not detected, add the `[` before the element.
- When the end of a new element is not detected, add `}` after the element.
- When the end of an element previously introduced is not detected, add `]` after the element.
- Alternatively, if you want plint to automatically determine which type of element is ending, use `|`.
- When an article should not create an element, add `#` to the beginning of that word. For terms that introduce multiple elements that contain multiple words (like "at least one"), it is necessary to place the `#` not at the first term (for example: `at #least one`) for the moment.
- When a claim element was introduced properly as a singular element but later referred to as plural, the character `!` can be used to erase the plural. For example, `[expected traffic delays!;` will be interpreted as `[expected traffic delay];`.
- Sometimes getting plint to properly parse claim elements requires adding text. Text put between backticks (`` ` ``) will be added to the claim for the antecedent basis check but not used otherwise. Here are some examples:
    - The limitation "upper and lower nozzles" should introduce an "upper nozzle" and a "lower nozzle". So, "upper and lower nozzles" could be marked as `` {upper `nozzle| `and {lower nozzles!| ``.
    - Sometimes claim elements are introduced properly as a plural element but later referred in plural. For example, a claim may introduce "adjacent TMEs" but later refer to "each adjacent TME". The latter can be marked as `` each {adjacent TME`s`| `` to add the plural for the antecedent basis checker.

See [demo-claims.txt](demo-claims.txt) below for the basic notation (`|`) in use.

    1. A contraption| comprising:
    an enclosure,
    a display,
    at least one button, and
    at least one widget| mounted on the enclosure,
    wherein the enclosure| is green,
    the at least one button| is yellow, and
    the at least one widget| is blue.

As commas, semi-colons, colons, and the end of a claim terminate claim elements, it is not necessary to mark claims like the following, though doing so is harmless:

    1. A contraption| comprising:
    an enclosure|,
    a display|,
    at least one button|, and
    at least one widget| mounted on the enclosure|,
    wherein the enclosure| is green,
    the at least one button| is yellow, and
    the at least one widget| is blue.

### Verbose mode

Verbose mode can be enabled with the `-V` or `--verbose` flag, which will print how plint is interpreting the claim when doing the antecedent basis analysis. For example, plint's interpretation of the demo claim is:

    Claim 1 marked: A {contraption} comprising: an {enclosure}, a {display}, {at least one button}, and {at least one widget} mounted on the [enclosure], wherein the [enclosure] is green, the [at least one button] is yellow, and the [at least one widget] is blue.

### Shortcomings of the antecedent basis checker

The antecedent basis checker is fragile and will likely require some iteration until a claim is marked in a way that plint likes.

At present, plint won't work with nested elements. For example: `a center of the widget|` would ideally be interpreted as `a {center of [the widget]}`, but that's not how plint will work at the moment. That'll need to be marked like this: `a center of #the widget|`, interpreted as `a {center of the widget}`. Then plint will think it's all just one element.

## Specification checking

If the optional `-s` or `--spec` flag is provided with a text file containing the specification of the patent application, plint will perform additional checks against the specifications.

The specification will be checked for paragraphs containing possible lexicographic definitions.

If both the specification checking and antecedent basis checking features are used, plint will check to make sure that all elements mentioned in the claims are present in the specification.

## Restriction checking

Analysis possibly useful to identify restrictions will be performed if the `-r` or `--restriction` flag is enabled. This requires that the claims be marked for antecedent basis and will automatically enable antecedent basis checking. All combinations of independent claims will be analyzed to identify elements common to the combination and elements unique to each claim being compared. Based on the elements common and unique to each claim, plint will identify possible restrictions based on the claims being unrelated/independent, related as combination-subcombination, or related as a distinct product and process pair. plint is not capable of recognizing other forms of restriction at the moment.

As plint's restriction checking only looks at claim elements, and not relationships between the elements, it is not a complete analysis.

If both the `-s`/`--spec` and `-r`/`--restriction` flags are enabled, a rudimentary analysis of the specification will be made to identify possible species elections.

## DAV claims viewer search string

If any warnings are printed, plint will display a string which can be pasted into the DAV claims viewer to highlight the terms found to have issues in the claims.

## Writing the output to a file

The optional `-o` or `--outfile` flag will write the warnings and DAV claims viewer search string to `{file}.out`, where `file` is the input file. For example, the following will write to `claims.txt.out`:

    plint claims.txt --outfile

## Other features of plint

### Endings mode

The `-e` or `--endings` flag will enable some checks based on word endings:

- Checks for adverbs by identifying words that end in -ly. These are frequently ambiguous.
- Checks for present participle words by identifying words that end in -ing. These often are functional terms that need to be checked for indefiniteness.

These checks are disabled by default as they return a large number of false positives.

### USPTO examiner mode

Some messages which are only relevant to USPTO patent examiners are displayed if the `-u` or `--uspto` flags.

### Nitpick mode

For my own convenience, `-n` or `--nitpick` is equivalent to `--ant-basis --endings --restriction --uspto`.

### Verbose and debug modes

A verbose mode which prints additional information can be enabled with `-V` or `--verbose`. At the moment, this will only display how plint is interpreting the claim when doing the antecedent basis analysis. A debug mode which will print even more information can be enabled with `-d` or `--debug`.

### JSON input file

For convenience, rather than keeping track of a large number of command line arguments, a JSON input file can be used where the names correspond to the (long) command line arguments. For example, `plint --ant-basis demo-claims.txt` is equivalent to running `plint demo.json` where demo.json is as follows:

    {
        "claims": "demo-claims.txt",
        "ant_basis": true
    }

The short command line arguments will not work in the JSON file. For example, replacing `ant_basis` with `"a": true`

If command line arguments conflict with the JSON file, the command line argument will be used, not what is written in the JSON file. The command line arguments override the JSON file.

### Title checking

The `-t` or `--title` command line flag will enable checking the title, which is given as the command line argument:

    plint --title "A novel title" demo-claims.txt

Per MPEP 606, titles should not start with "An" or contain the word "novel", so this example would return two warnings.

## Exit statuses

- 0 means the claims pass all tests.
- 1 means that a fatal error occurred in the parsing of the claims. Typically the claims will be written in a way that violates plint's expectations for how a claim will be structured.
- 2 means that one or more warnings were made.
