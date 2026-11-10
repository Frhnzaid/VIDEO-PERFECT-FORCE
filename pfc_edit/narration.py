"""Voice-over script and TTS for the PFC client video.

Text is written for the ear: "P-F-C" so the voice spells it out, numbers in
words. Every line describes what is on screen or restates the client's SOP;
no figures are added beyond those the client gave (5,600 psi test pressure).

    python pfc_edit/narration.py --voice en_US-ryan-high.onnx --out work/vo

Lines are placed on the timeline by build.py:
  "3d"     seconds from the start of a 3D step (key from pfc_steps.STEPS)
  "src_at" a time in the source footage (follows the edit)
  "at"     an absolute time on the new timeline ("outro" = from outro start)
"""
import argparse
import json
import os
import subprocess
import sys
import wave

LINES = [
    # intro
    dict(id="intro", at=0.8,
         text="Perfect Force Clamp. A hot bolting solution by Perfect Emerald."),
    # 3D how it works
    dict(id="3d_est", step="est", off=0.3,
         text="Here is how the P-F-C lets flange stud bolts be replaced, "
              "while the line stays under pressure."),
    dict(id="3d_A1", step="A1", off=0.3,
         text="Step one. Apply Molykote anti-seize to the threads and nut faces "
              "of the P-F-C stud bolts, and the new stud bolts."),
    dict(id="3d_A2", step="A2", off=0.3,
         text="Step two. Measure the flange gap at four sides, in a criss-cross pattern. "
              "The widest gap is marked number one."),
    dict(id="3d_A3", step="A3", off=0.3,
         text="Step three. Torque the existing stud bolts to one hundred percent "
              "of the client's value, then sound-check each bolt."),
    dict(id="3d_B4", step="B4", off=0.3,
         text="Step four. Install the P-F-C on the flange. The male and female segments "
              "interlock, with the slots aligned and fully seated."),
    dict(id="3d_B5", step="B5", off=0.3,
         text="Step five. Hand-tighten the P-F-C stud bolts, until the clamp is in "
              "full contact with the flange faces."),
    dict(id="3d_B6", step="B6", off=0.3,
         text="Step six. Check that the P-F-C gap is within tolerance, "
              "and equal to the measured flange gap."),
    dict(id="3d_B7", step="B7", off=0.3,
         text="Step seven. Set the grub screws. Position one first, "
              "then the others in criss-cross order."),
    dict(id="3d_B8", step="B8", off=0.3,
         text="Step eight. Torque the P-F-C stud bolts in three stages. Thirty, sixty, "
              "and one hundred percent. Then a rolling pass, and a sound check."),
    dict(id="3d_C9", step="C9", off=0.3,
         text="Step nine. Check the wind direction, and position the workers upwind."),
    dict(id="3d_C10", step="C10", off=0.3,
         text="Step ten. Replace the flange stud bolts one at a time, starting opposite "
              "the workers. A hammer wrench holds the far nut. Each new bolt is torqued "
              "with a calibrated torque wrench."),
    dict(id="3d_C11", step="C11", off=0.3,
         text="Step eleven. Sound-check all the new stud bolts."),
    dict(id="3d_D12", step="D12", off=0.3,
         text="Step twelve. Loosen the P-F-C stud bolts, starting farthest from the "
              "workers, and remove the clamp."),
    dict(id="3d_hero", step="hero", off=0.4,
         text="Four new stud bolts. And the line stayed under pressure throughout."),
    # footage
    dict(id="ft_install", src_at=13.0,
         text="Next, the Perfect Force Clamp is installed on a live test assembly."),
    dict(id="ft_callouts", src_at=24.6,
         text="The clamp holds the joint, so each flange stud bolt can be replaced."),
    dict(id="ft_assembly", src_at=97.0,
         text="Installation continues on the test assembly."),
    dict(id="ft_hydro", src_at=206.0,
         text="The assembly is then hydrotested, at a test pressure of "
              "five thousand six hundred P-S-I."),
    dict(id="ft_gauge", src_at=213.5,
         text="A pressure gauge monitors the test pressure."),
    dict(id="ft_chart", src_at=244.5,
         text="A chart recorder logs the pressure throughout the test."),
    dict(id="ft_complete", src_at=326.6,
         text="The complete test assembly, during the hydrotest."),
    dict(id="ft_result", src_at=350.7,
         text="And the recorded pressure chart."),
    # outro
    dict(id="outro", outro=0.6,
         text="Perfect Force Clamp. By Perfect Emerald, Sendirian Berhad. "
              "Visit perfect emerald dot com."),
]


def wav_duration(path):
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())


def synth(voice, out_dir, length_scale=1.06):
    os.makedirs(out_dir, exist_ok=True)
    durs = {}
    for ln in LINES:
        path = os.path.join(out_dir, ln["id"] + ".wav")
        raw = path + ".raw.wav"
        if not os.path.exists(path):
            subprocess.run([sys.executable, "-m", "piper", "-m", voice, "-f", raw,
                            "--length-scale", str(length_scale),
                            "--sentence-silence", "0.25"],
                           input=ln["text"].encode(), check=True,
                           stderr=subprocess.DEVNULL)
            # light broadcast polish: high-pass, gentle compression, loudness
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                            "highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
                            "loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000",
                            "-ac", "1", path], check=True)
            os.remove(raw)
        durs[ln["id"]] = round(wav_duration(path), 3)
    with open(os.path.join(out_dir, "durations.json"), "w") as f:
        json.dump(durs, f, indent=1)
    return durs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    for k, v in synth(a.voice, a.out).items():
        print(f"{k:12s} {v:6.2f}s")


if __name__ == "__main__":
    main()
