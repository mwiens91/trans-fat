"""This contains instructions to auto rename directories.  First give a
search regex to identify a directory to rename, then give regex for the
groups to parse in the original name (make sure to match the whole name,
so backreferencing in Python will work properly) then give a new name
that uses the groups matched. See the function re.sub at
https://docs.python.org/3/library/re.html#re-objects.
"""

name_patterns = [

# Above and Beyond - Group Therapy
# example: Above and Beyond - Group Therapy 190 (2016-07-15) (Vyze) -> ABGT_190
[r'(Above and Beyond)(.+)(\(Vyze\))', r'.*\s(\d{3})\s.*', r'ABGT_\1'],

# Armin van Buuren - A State of Trance
# example: Armin van Buuren - A State Of Trance 826 (10.08.2017) SBD Split Tracks -> ASOT_826
[r'(Armin van Buuren)(.+)(SBD Split Tracks)', r'.*\s(\d{3}(?:\.\d)?)\s.*', r'ASOT_\1'],

]
