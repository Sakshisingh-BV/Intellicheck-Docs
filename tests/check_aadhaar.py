#!/usr/bin/env python
"""Quick check of the Aadhaar number Verhoeff checksum."""

d = [
    [0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0]
]
p = [
    [0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]
]

uid = "286516146355"
c = 0
for i, digit in enumerate(reversed(uid)):
    c = d[c][p[i % 8][int(digit)]]
print(f"Aadhaar {uid}: checksum c={c}, valid={c==0}")
print(f"Starts with 0 or 1: {uid[0] in ('0', '1')}")

# Also check the wrong one
uid2 = "161463551947"
c = 0
for i, digit in enumerate(reversed(uid2)):
    c = d[c][p[i % 8][int(digit)]]
print(f"\nWrong Aadhaar {uid2}: checksum c={c}, valid={c==0}")
print(f"Starts with 0 or 1: {uid2[0] in ('0', '1')}")
