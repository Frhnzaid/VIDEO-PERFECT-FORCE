"""Shared timing for the 3D hot bolting animation and its text overlay.

Steps follow section 8.5 'Hot Bolting Sequence Using PFC' of the client's SOP.
Times are seconds from the start of the 3D clip (24 fps).
"""

# Step lengths are set so each voice-over line (narration.py) fits with a
# short pause: max(original pace, voice length + 1.2 s).
# key, phase, SOP step no., duration, title, detail
_STEPS = [
    ("est", None, None, 6.4, "", ""),
    ("A1", "A", 1, 8.9, "Apply Molykote",
     "Anti-seize on the threads and nut faces of the PFC and new stud bolts"),
    ("A2", "A", 2, 7.9, "Measure the flange gap",
     "Caliper at four sides, criss-cross. Widest gap marked No. 1"),
    ("A3", "A", 3, 8.0, "Torque existing stud bolts",
     "100% of the client torque value, then sound-check each bolt"),
    ("B4", "B", 4, 9.4, "Install the PFC",
     "Male and female segments interlocked, slots aligned, fully seated"),
    ("B5", "B", 5, 7.7, "Hand-tighten PFC stud bolts",
     "Until the PFC is in full contact with the flange faces"),
    ("B6", "B", 6, 6.8, "Check the PFC gap",
     "Caliper: within tolerance and equal to the measured flange gap"),
    ("B7", "B", 7, 7.0, "Set the grub screws",
     "No. 1 (widest gap) first, then the others in criss-cross order"),
    ("B8", "B", 8, 10.4, "Torque PFC stud bolts",
     "30%, 60%, 100% from No. 1, rolling pass at 100%, then sound-check"),
    ("C9", "C", 9, 5.5, "Position workers upwind",
     "Check the wind direction before opening the joint"),
    ("C10", "C", 10, 18.0, "Replace stud bolts one at a time",
     "Start opposite the workers. Nut stopper on the far nut. "
     "Torque each new bolt with a calibrated MTW"),
    ("C11", "C", 11, 4.4, "Sound-check new stud bolts",
     "All four replacement stud bolts"),
    ("D12", "D", 12, 7.0, "Remove the PFC",
     "Loosen PFC stud bolts farthest from the workers first, then remove the PFC"),
    ("hero", None, None, 5.0, "", ""),
]
STEPS = []
_t = 0.0
for _k, _ph, _no, _d, _ti, _de in _STEPS:
    STEPS.append((_k, _ph, _no, round(_t, 3), round(_t + _d, 3), _ti, _de))
    _t += _d
DUR = {k: d for k, _, _, d, _, _ in _STEPS}

PHASES = [("A", "FLANGE PREPARATION", "PREPARATION"),
          ("B", "INSTALLATION OF THE PFC", "INSTALL PFC"),
          ("C", "REPLACEMENT OF FLANGE STUD BOLTS", "REPLACE BOLTS"),
          ("D", "REMOVAL OF THE PFC", "REMOVE PFC")]

TOTAL = STEPS[-1][4]
S = {k: (t0, t1) for k, _, _, t0, t1, _, _ in STEPS}

# numbering (criss-cross) of the four sides, used for gap marks, grub screws and
# PFC stud bolts: No. 1 top, No. 2 bottom, No. 3 one side, No. 4 the other
SIDE_ORDER = [90, 270, 0, 180]
# workers stand on the camera (-Y) side; wind blows from them towards the flange.
# Flange stud bolts are replaced starting opposite the workers (+Y side)
FLANGE_ORDER_ANG = [45, 225, 135, 315]
# PFC stud bolts are loosened farthest from the workers first
PFC_LOOSEN_ANG = [0, 90, 270, 180]

# B8 torque rounds: three stages x four bolts, then a rolling pass and sound check
B8_T0 = S["B8"][0] + 0.3
B8_STEP = (DUR["B8"] - 0.3 - 1.4 - 1.0) / 12
B8_ROLL = B8_T0 + 12 * B8_STEP
# C10: one stud bolt per quarter of the step
C10_SPAN = DUR["C10"] / 4
