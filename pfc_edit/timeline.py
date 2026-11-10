"""Edit decision lists. Times for "src" items are seconds in the ORIGINAL video;
overlay "at" times are seconds on the NEW timeline.

Source map (pfc_demo.mp4, 6:00):
  0.00 -   7.25  old logo intro (burnt-in)          -> replaced by new intro
  7.25 -  12.25  "Perfect Force Installation" title -> dropped (burnt-in text)
 12.25 - 200.17  installation footage
200.17 - 205.17  "Hydrotest Testing Pressure" title -> dropped (burnt-in text)
205.17 - 350.04  hydrotest / pressure gauge / chart recorder
350.04 - 360.05  "Thank You For Watching" (burnt-in) -> replaced by new outro
"""

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
}
