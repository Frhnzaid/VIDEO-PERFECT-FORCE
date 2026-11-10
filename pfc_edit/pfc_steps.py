"""Shared timing for the 3D hot bolting animation and its text overlay.

Steps follow section 8.5 'Hot Bolting Sequence Using PFC' of the client's SOP.
Times are seconds from the start of the 3D clip (24 fps).
"""

# key, phase, SOP step no., start, end, title, detail
STEPS = [
    ("est", None, None, 0.0, 3.0, "", ""),
    ("A1", "A", 1, 3.0, 7.5, "Apply Molykote",
     "Anti-seize on the threads and nut faces of the PFC and new stud bolts"),
    ("A2", "A", 2, 7.5, 13.0, "Measure the flange gap",
     "Caliper at four sides, criss-cross. Widest gap marked No. 1"),
    ("A3", "A", 3, 13.0, 18.0, "Torque existing stud bolts",
     "100% of the client torque value, then sound-check each bolt"),
    ("B4", "B", 4, 18.0, 24.5, "Install the PFC",
     "Male and female segments interlocked, slots aligned, fully seated"),
    ("B5", "B", 5, 24.5, 28.0, "Hand-tighten PFC stud bolts",
     "Until the PFC is in full contact with the flange faces"),
    ("B6", "B", 6, 28.0, 31.0, "Check the PFC gap",
     "Caliper: within tolerance and equal to the measured flange gap"),
    ("B7", "B", 7, 31.0, 34.5, "Set the grub screws",
     "No. 1 (widest gap) first, then the others in criss-cross order"),
    ("B8", "B", 8, 34.5, 44.0, "Torque PFC stud bolts",
     "30%, 60%, 100% from No. 1, rolling pass at 100%, then sound-check"),
    ("C9", "C", 9, 44.0, 46.5, "Position workers upwind",
     "Check the wind direction before opening the joint"),
    ("C10", "C", 10, 46.5, 64.5, "Replace stud bolts one at a time",
     "Start opposite the workers. Nut stopper on the far nut. "
     "Torque each new bolt with a calibrated MTW"),
    ("C11", "C", 11, 64.5, 67.0, "Sound-check new stud bolts",
     "All four replacement stud bolts"),
    ("D12", "D", 12, 67.0, 73.5, "Remove the PFC",
     "Loosen PFC stud bolts farthest from the workers first, then remove the PFC"),
    ("hero", None, None, 73.5, 77.0, "", ""),
]

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

# B8 torque rounds: three stages x four bolts, then a rolling pass
B8_T0, B8_STEP = S["B8"][0] + 0.2, 0.6
B8_ROLL = B8_T0 + 12 * B8_STEP
# C10: one stud bolt every 4.5 s
C10_SPAN = 4.5
