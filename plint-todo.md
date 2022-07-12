# plint to-do list

- Check for invalid multiple dependencies.
- Check for features of other softwares.
- `--reject` option to write rejections to text file. Then you can delete the ones you don't want.
- "Use" claim detection: method or process without word step?
- Check classification for patent documents on patent analysis for more ideas.
- Check for synonyms of the relative terms you already have for more.
- Optional argument `--specs` to check that each element is mentioned in the specs.
- For `--specs`, also check that each element has a reference number. If an element does not, that could indicate a drawing objection is needed for that element.
- Add `--stats` to print out the number of words in each claim and other statistics.
- Add ability to annotate the claim to ignore a particular word for the warnings file. Add this to the documentation after doing so: If a user wishes to prevent rules from being applied to a particular word, they can add "#" to the beginning of the word. For example, they could change *element* to *#element*.
- Look at typo for ideas: Statistical method of finding mistakes in patent claims? <https://ieeexplore.ieee.org/abstract/document/6593963>
- Look at readability indices to identify convoluted parts of claims to double check.
    - <https://en.wikipedia.org/wiki/Readability>
    - <https://stackoverflow.com/questions/46759492/syllable-count-in-python>
    - <https://en.wikipedia.org/wiki/Automated_readability_index>: No syllables needed.
- Detect ranges of numbers, print warning when multiple are found in one claim as that could indicate a 112(b) issue. For dependent claims, check that the range is fully within the range of the independent claims. See TC 3700 112(b) refresher for examples.
- Print some checks for equations like dimensional homogeneity, no singularities.
    - `\b(equation|formula)\b`
    - `=`
- Check alderucci_using_2020 for more ideas.
- From my notes: "Can't claim a hole alone. Need to claim a wall, etc., and then claim the hole in that." Terms to consider: hole(s), gap(s), opening(s), aperture(s), space, spacing
- Give warnings for "consisting of" and "consisting essentially of".
- Make an actual version number.
- 101 rejections: Claiming a human:
    - MOPP 14.131: ""when in use", "when held by an operator"
        - <https://www.gov.uk/guidance/manual-of-patent-practice-mopp/section-14-the-application>
    - <https://www.uspto.gov/web/offices/pac/mpep/s2105.html>
    - <https://patentlyo.com/patent/2012/12/ex-parte-kamrava.html>
        - embryo
    - <https://www.degruyter.com/document/doi/10.1515/jbbbl-2021-2002/html?lang=en>
        - fetus
        - embryo
        - chimera
        - human
- `\b(reaction|reacting|combustion|combusting) rate\b`
    - `\brate of (reaction|reacting|combustion|combusting)\b`
    - Check notes for 16401465 ("combustion rate").
- <https://www.jpo.go.jp/e/system/laws/rule/guideline/patent/tukujitu_kijun/document/index/02_0203_e.pdf>
- flow rate: mass or volumetric?
- vague terms: amount, quantity, substance, material
- Rewrite to handle filtering without duplicate code.
- Think about how to reduce the amount of manual annotation needed.
- Give warnings for more than 3 independent claims and more than 20 total claims (or whatever the number for that is; check), in order to get the extra hour.
- Reorganize code to have unit tests for everything including the antecedent basis checking.
- Types of relative terms:
    - imprecise (like what you have at present)
    - relative without reference (Check that claim mentions what it is relative to.)
        - increases/increasing
        - decreases/decreasing
        - more/greater
        - less
        - reduces/reducing
        - narrows
        - narrower # 15525613
- Get ends of claim elements from numbered elements in specs? Scan specs for text between a/an and a number?

***

https://www.geeksforgeeks.org/python-extract-substrings-between-brackets/

>>> import re
>>> test_str = "A (device) comprising a (widget) and a (display), where the (diameter of the (widget)) is larger than the (diameter of the (display))."
>>> re.findall(r'\(.*?\)', test_str)
['(device)', '(widget)', '(display)', '(diameter of the (widget)', '(diameter of the (display)']
