# patent-tools

Here are a collection of Python scripts that I find useful for patent examination. They are designed to run on the ancient version of Python the USPTO puts on their computers, so they won't use the latest developments in Python. And the Python installation is limited to the standard library, so NLTK can not be used.

## Contents

- [plint: patent claim linter](plint.md)
- jplatpat-cls.py: List most popular JPFI and IPC classifications given one or more search result CSV files from [J-PlatPat](https://www.j-platpat.inpit.go.jp/).
- jplatpat-to-brs.py: Convert a search result CSV file from J-PlatPat to a list of JP patent document IDs in BRS format, that is, that can be read by PE2E Search.
- TODO: Implementation of [search theory from Phillip Morse](https://apps.dtic.mil/sti/citations/AD0702920) to more efficiently search.

## Legal

This work was prepared or accomplished by Ben Trettel in his personal capacity. The views expressed are his own and do not necessarily reflect the views or policies of the United States Patent and Trademark Office, the Department of Commerce, or the United States government.
