"""Edit decision lists. Times for "src" items are seconds in the ORIGINAL video;
overlay "at" times are seconds on the NEW timeline.

Source map (pfc_demo.mp4, 6:00):
  0.00 -   7.25  old logo intro (burnt-in)          -> replaced by new intro
  7.25 -  12.25  "Perfect Force Installation" title -> dropped (burnt-in text)
 12.25 - 200.17  installation footage
200.17 - 205.17  "Hydrotest Testing Pressure" title -> dropped (burnt-in text)
205.17 - 355.04  hydrotest / pressure gauge / chart recorder / chart result
355.04 - 360.05  "Thank You For Watching" (burnt-in) -> replaced by new outro

New-timeline mapping for the full edit:
  part 1 (src 12.25-200.17):  new = src - 6.25
  part 2 (src 205.17-355.04): new = src - 11.25

"""
from gfx import PFC3D_TOTAL, SEQ_TOTAL

TIMELINES = {
    # ~15.75 s style preview: intro -> wipe -> first installation shots
    "preview": {
        "sequence": [
            {"type": "intro", "dur": 6.0},
            {"type": "src", "in": 12.25, "out": 22.0},
        ],
        "wipe_after": [0],
        "overlays": [
            {"type": "lower_third", "at": 7.0, "dur": 5.0,
             "args": {"kicker": "STEP 01", "title": "PERFECT FORCE CLAMP INSTALLATION"}},
            {"type": "callout", "at": 12.95, "dur": 2.8,
             "args": {"cx": 1830, "cy": 1300, "r": 300, "label": "PFC CLAMP"}},
        ],
        "audio_start": 0.0,
    },

    # full client edit, ~6:35 (3D how-it-works)
    "full": {
        "sequence": [
            {"type": "intro", "dur": 6.0},
            {"type": "frames3d", "dur": PFC3D_TOTAL},   # 3D how-it-works (pfc3d.py)
            {"type": "src", "in": 12.25, "out": 200.17},
            {"type": "src", "in": 205.17, "out": 355.04},
            {"type": "outro", "dur": 8.0},
        ],
        "wipe_after": [0, 1, 2, 3],
        # overlays placed by source time (src_at), so they follow the footage
        "overlays": [
            # --- STEP 01: installation ------------------------------------
            {"type": "lower_third", "src_at": 13.25, "dur": 5.0,
             "args": {"kicker": "STEP 01", "title": "PERFECT FORCE CLAMP INSTALLATION"}},
            {"type": "callout", "src_at": 19.2, "dur": 2.8,
             "args": {"cx": 1830, "cy": 1300, "r": 300, "label": "PFC CLAMP"}},
            {"type": "callout", "src_at": 24.5, "dur": 3.2,
             "args": {"cx": 3150, "cy": 1650, "r": 430, "label": "FLANGE", "side": "left"}},
            {"type": "callout", "src_at": 28.85, "dur": 3.2,
             "args": {"cx": 3005, "cy": 1505, "r": 120, "label": "STUD BOLT & NUT",
                      "side": "left", "rise": 420, "run": 260}},
            {"type": "lower_third", "src_at": 96.85, "dur": 5.0,
             "args": {"kicker": "STEP 01 \u00b7 INSTALLATION", "title": "TEST ASSEMBLY"}},
            # --- STEP 02: hydrotest ---------------------------------------
            {"type": "lower_third", "src_at": 205.85, "dur": 5.5,
             "args": {"kicker": "STEP 02", "title": "HYDROTEST PRESSURE TESTING",
                      "sub": "Test pressure: 5,600 psi"}},
            {"type": "callout", "src_at": 212.0, "dur": 3.6,
             "args": {"cx": 1940, "cy": 900, "r": 310, "label": "PRESSURE GAUGE"}},
            {"type": "lower_third", "src_at": 244.25, "dur": 5.0,
             "args": {"kicker": "STEP 02 \u00b7 HYDROTEST", "title": "PRESSURE CHART RECORDER"}},
            {"type": "lower_third", "src_at": 326.35, "dur": 5.0,
             "args": {"kicker": "STEP 02 \u00b7 HYDROTEST", "title": "COMPLETE TEST ASSEMBLY"}},
            {"type": "lower_third", "src_at": 350.45, "dur": 4.1,
             "args": {"kicker": "RESULT", "title": "RECORDED PRESSURE CHART"}},
        ],
        "audio_start": 0.0,
    },

    # same edit with the 2D schematic explainer (no Blender frames needed)
    "full2d": None,
}

TIMELINES["full2d"] = dict(TIMELINES["full"])
TIMELINES["full2d"]["sequence"] = [
    {"type": "how_it_works", "dur": SEQ_TOTAL} if it["type"] == "frames3d" else it
    for it in TIMELINES["full"]["sequence"]]
