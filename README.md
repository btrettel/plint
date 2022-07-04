# patent-tools

Here are a collection of Python scripts that I find useful for patent examination. They are designed to run on the ancient version of Python the USPTO puts on their computers, so they won't use the latest developments in Python. And the Python installation is limited to the standard library, so NLTK can not be used.

- [plint.py: Patent Claim Linter](plint.md)
- jplatpat-to-brs.py: Convert a search result CSV file from [J-PlatPat](https://www.j-platpat.inpit.go.jp/) to a list of JP patent document IDs in BRS format, that is, that can be read by PE2E Search.
- TODO: Implementation of [search theory from Phillip Morse](https://apps.dtic.mil/sti/citations/AD0702920) to more efficiently search.
