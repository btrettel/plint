# plint: patent claim linter

Current version: 0.1.3

plint analyzes a text file containing patent claims for 112(b), 112(d), 112(f), and other issues.

plint is designed to run on the ancient version of Python the USPTO has on their computers, so plint won't use the latest features of Python. And the USPTO Python version is limited to the standard library, so NLTK can not be used.

## Disclaimer

This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.

## Usage

First, keep in mind MPEP 2173.02.II:

> Examiners should note that Office policy is not to employ *per se* rules to make technical rejections. Examples of claim language which have been held to be indefinite set forth in MPEP 2173.05(d) are fact specific and should not be applied as *per se* rules.

Warnings produced by plint are *possible* rejections or objections. Each should be carefully checked as many warnings will not be valid rejections or objections.

### Windows

On my USPTO computer (Windows), after adding `C:\Python32` and the folder where plint.py is to my path, I can run the script as follows:

    python.exe plint.py .\claims.txt

You can edit your path by using the start search button. Search for env and click on "Edit environment variables for your account". Separate the different folder paths with a semi-colon. [See here](https://answers.microsoft.com/en-us/windows/forum/all/adding-path-variable/97300613-20cb-4d85-8d0e-cc9d3549ba23) for some screenshots of the environmental variables dialog box.

If you want to run the script directly instead of through Python, you can add ;.PY to the end of the user environmental variable PATHEXT. For me, this means that I added PATHEXT in the "Edit environment variables for your account" dialog as follows:

    .COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL;.PY

Then I can run plint as follows:

    plint.py .\claims.txt

### Linux

On Linux, the plint.py script can be run from the directory it is in as follows:

    ./plint.py claims.txt

claims.txt is the file you wish to read, which is plain text containing the patent document claims. Each claim is numbered with a period after the number, for example: "1."

Alternatively, you can add the directory plint.py is in to your PATH and then run plint as follows:

    plint.py claims.txt

### Verbose and debug modes

A verbose mode which prints additional information can be enabled with `-V` or `--verbose`. At the moment, this will only display how plint is interpreting the claim when doing the antecedent basis analysis. A debug mode which will print even more information can be enabled with `-d` or `--debug`.

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

## Warnings file

A warnings file is used to identify possibly problematic claim language.

The standard warnings file ([warnings.csv](warnings.csv)) can be modified to add or remove warnings as desired by the user. The format of this file is as follows: The first column is "regex", which contains regular expressions to match against the claims. The second column is "message", which lists the message displayed when the regex is matched. The file must start with a line listing the columns as "regex" and "message".

As an example, consider the following line:

    \belement\b,Possible 112(f) invocation. See MPEP 2181.

The `\b` code means *word boundary* in regular expressions, so this line will match the word *element* but not match *elemental*. After the comma is the message displayed, including a convenient MPEP reference useful to determine whether claim language caught by this line meets 112(f).

An external warnings file can be called with the `--warnings` flag.

Specific warnings can be disabled in a warnings file without the line being deleted by adding "#" to the beginning of the regex column of a warning. Comments can be added in the warning column; all text after "#" will not be printed in plint.

Warnings with warning text containing the terms "112(d)" or "DEPONLY" will only apply to dependent claims. This is true even if "DEPONLY" is only printed in a comment.

### Standard warnings file philosophy

In warnings.csv, before adding a line related to patent prosecution, I ask whether more than 1% of examiners would reject a claim based on the presence of a particular word or phrase. I don't ask whether the rejection would be valid. warnings.csv is meant to be conservative in that it will have far more warnings than rejections I would actually make. It represents rejections (valid or not) that an applicant might possible face.

I also include some lines meant to point out unnecessarily narrow claim limitations that may be of interest outside of patent prosecution.

## Filtering out warnings

Warnings can be disabled from the command line by filtering out any part of the warning message printed using the `--filter` flag followed by one or more regular expressions. For example, to filter out all warnings containing the text "112(f)":

    plint.py claims.txt --filter "112\(f\)"

Then no warnings where the text contains "112(f)" will be printed. (The quotes are necessary to prevent the shell from interpreting the parentheses. And the parentheses are escaped as parentheses have a special function in regular expressions.) Multiple filters can be applied as well:

    plint.py claims.txt --filter "112\(f\)" antecedent

(As can be seen, no quotes or parentheses are necessary for single words without any special characters like "antecedent". However, multiple words will require quotes, for example: "antecedent basis" should be quoted.)

The filtering applies to all warnings, not just warnings from a warnings file.

## Antecedent basis checking

Checking for antecedent basis issues requires using the optional flag `-a` or `--ant-basis`. This is optional because the feature requires the claims file to use a special syntax as it is difficult to automatically recognize the start and end of claim elements. plint will recognize that the terms "a", "an", "at least one", and "one or more" will appear before new claim elements and that the words "the" or "said" will appear before claim elements previously introduced. plint will also know that a claim element ends when a semi-colon, comma, or colon appear, and at the end of a claim.

To check the demo claims on Linux:

    ./plint.py -a demo-claims.txt

The special syntax for antecedent basis issues is as follows: When the start of a new element is not detected, add `{` before the element. When the start of an element previously introduced is not detected, add the `[` before the element. When the end of a new element is not detected, add `}` after the element. When the end of an element previously introduced is not detected, add `]` after the element. Alternatively, if you want plint to automatically determine which type of element is ending, use `|`. When an article should not create an element, add "#" to the beginning of that word. See [demo-claims.txt](demo-claims.txt) below for this notation in use.

    1. A contraption| comprising:
    an enclosure,
    a display,
    at least one button, and
    at least one widget| mounted on the enclosure,
    wherein the enclosure| is green,
    the at least one button| is yellow, and
    the at least one widget| is blue.

As commas, semi-colons, colons, and the end of a claim terminate claim elements, it is not necessary to annotate claims like the following, though doing so is harmless:

    1. A contraption| comprising:
    an enclosure|,
    a display|,
    at least one button|, and
    at least one widget| mounted on the enclosure|,
    wherein the enclosure| is green,
    the at least one button| is yellow, and
    the at least one widget| is blue.

Verbose mode can be enabled with the `-V` or `--verbose` flag, which will print how plint is interpreting the claim when doing the antecedent basis analysis. For example, plint's interpretation of the demo claim is:

    Claim 1 annotated: a {contraption} comprising: an {enclosure}, a {display}, {at least one button}, and {at least one widget} mounted on the [enclosure], wherein the [enclosure] is green, the [at least one button] is yellow, and the [at least one widget] is blue.

The antecedent basis functionality of plint may be fragile and will likely require some iteration until a claim is annotated in a way that plint likes.

At present, plint won't work with nested elements. For example: `a center of the widget|` would ideally be interpreted as `a {center of [the widget]}`, but that's not how plint will work at the moment. That'll need to be annotated like this: `a center of #the widget|`, interpreted as `a {center of the widget}`. Then plint will think it's all just one element.

If a specific claim element is introduced more than once, a warning will be printed. For example, the following claim will produce a warning:

    1. A device comprising:
    a widget;
    a widget.

## DAV claims viewer search string

If any warnings are printed, plint will display a string which can be pasted into the DAV claims viewer to highlight the terms found to have issues in the claims.

## Writing the output to a file

The optional `-o` or `--outfile` flag will write the warnings and DAV claims viewer search string to `{file}.out`, where `file` is the input file. For example, the following will write to `claims.txt.out`:

    plint.py claims.txt --outfile

## Exit statuses

- 0 means the claims pass all tests.
- 1 means that a fatal error occurred in the parsing of the claims. Typically the claims will be written in a way that violates plint's expectations for how a claim will be structured.
- 2 means that one or more warnings were made.

## Other scripts here

- jplatpat-cls.py: List most popular JPFI and IPC classifications given one or more search result CSV files from [J-PlatPat](https://www.j-platpat.inpit.go.jp/).
- jplatpat-to-brs.py: Convert a search result CSV file from J-PlatPat to a list of JP patent document IDs in BRS format, that is, that can be read by PE2E Search.
- TODO: Implementation of [search theory from Philip M. Morse](https://apps.dtic.mil/sti/citations/AD0702920) to more efficiently search.
- TODO: Write script to figure out which documents from J-PlatPat aren't on PE2E Search.
