"""Build the Perfect Force Clamp client video.

    python pfc_edit/build.py preview  --src pfc_demo.mp4 --out output/pfc_preview.mp4
    python pfc_edit/build.py full     --src pfc_demo.mp4 --out output/pfc_demo_client.mp4

The source file is only read, never written.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx  # noqa: E402
from timeline import TIMELINES  # noqa: E402

W, H, FPS = gfx.W, gfx.H, gfx.FPS

# Source is 3816x2160 with 36px black bars top and bottom (3816x2088 active).
# Crop the bars, scale to fill UHD 3840x2160, then grade.
GRADE = ",".join([
    "crop=3816:2088:0:36",
    "scale=3947:2160:flags=lanczos",
    "crop=3840:2160",
    "eq=contrast=1.08:saturation=1.12:gamma=0.96:brightness=-0.01",
    "colorbalance=rs=-0.03:gs=-0.005:bs=0.035:rh=0.025:gh=0.01:bh=-0.02",
    "curves=all='0/0 0.06/0.04 0.25/0.22 0.5/0.5 0.78/0.81 1/0.98'",
    "cas=0.45",
    "setsar=1",
    f"fps={FPS}",
    "format=yuv420p",
])

GFX_FUNCS = {
    "intro": (gfx.intro, True),
    "outro": (gfx.outro, True),
    "wipe": (gfx.wipe, False),
    "lower_third": (gfx.lower_third, False),
    "callout": (gfx.callout, False),
    "how_it_works": (gfx.how_it_works, True),
    "pfc3d_overlay": (gfx.pfc3d_overlay, False),
}


def run(cmd):
    print("+", " ".join(cmd[:6]), "...", flush=True)
    subprocess.run(cmd, check=True)


def render_gfx(kind, dur, path, logo, **kw):
    """Render one graphic to a video file (opaque -> h264, alpha -> qtrle)."""
    if os.path.exists(path):
        return path
    fn, opaque = GFX_FUNCS[kind]
    if kind in ("intro", "outro"):
        kw["logo"] = logo
    if opaque:
        enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p"]
    else:
        enc = ["-c:v", "qtrle", "-pix_fmt", "argb"]
    tmp = path + ".part" + os.path.splitext(path)[1]
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", *enc, tmp],
        stdin=subprocess.PIPE)
    for frame in gfx.render_frames(fn, dur, opaque=opaque, **kw):
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed rendering {kind}")
    os.replace(tmp, path)
    return path


def probe_duration(path, stream="a"):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", f"{stream}:0",
                        "-show_entries", "stream=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def audio_chain(inp, a0, total, src_dur, out_label, splice_at=200.0, xfade=4.0):
    """Original soundtrack for `total` seconds.

    When the new edit is longer than the source track, a section of the music is
    repeated with a crossfade at `splice_at`, so the song still ends on its own
    outro instead of cutting to silence.
    """
    tail = (f"afade=t=in:st=0:d=0.6,"
            f"afade=t=out:st={max(total - 2.5, 0):.3f}:d=2.5[{out_label}]")
    avail = src_dur - a0
    if total <= avail:
        return (f"[{inp}]atrim=start={a0}:duration={total:.3f},asetpts=PTS-STARTPTS," + tail)
    # len = (splice_at - a0) + (src_dur - y) - xfade == total
    y = splice_at - (total - avail) - xfade
    return (f"[{inp}]asplit=2[ma][mb];"
            f"[ma]atrim=start={a0}:end={splice_at:.3f},asetpts=PTS-STARTPTS[m1];"
            f"[mb]atrim=start={y:.3f},asetpts=PTS-STARTPTS[m2];"
            f"[m1][m2]acrossfade=d={xfade}:c1=tri:c2=tri,"
            f"atrim=duration={total:.3f}," + tail)


def build(name, src, out, work, logo_path, crf, preset, frames3d=None):
    tl = TIMELINES[name]
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if os.path.abspath(out) == os.path.abspath(src):
        raise SystemExit("Refusing to overwrite the source video.")
    logo = gfx.load_logo(logo_path)

    inputs, vlabels, filters = [], [], []
    n_in = [0]

    def add_input(*args):
        inputs.extend(args)
        n_in[0] += 1
        return n_in[0] - 1

    t = 0.0
    joins = []
    extra_overlays = []
    # ---- picture: main sequence ------------------------------------------
    for i, item in enumerate(tl["sequence"]):
        if item["type"] == "src":
            idx = add_input("-ss", f"{item['in']:.3f}", "-to", f"{item['out']:.3f}", "-i", src)
            filters.append(f"[{idx}:v]{GRADE},setpts=PTS-STARTPTS[v{i}]")
            dur = item["out"] - item["in"]
        elif item["type"] == "frames3d":
            # Blender PNG sequence (pfc3d.py), upscaled to UHD, with its text overlay
            if not frames3d or not os.path.isdir(frames3d):
                raise SystemExit("this timeline needs --frames3d DIR (output of pfc3d.py)")
            dur = item["dur"]
            idx = add_input("-framerate", str(FPS), "-start_number", "1",
                            "-i", os.path.join(frames3d, "f_%05d.png"))
            filters.append(f"[{idx}:v]scale={W}:{H}:flags=lanczos,unsharp=5:5:0.4,"
                           f"setsar=1,fps={FPS},format=yuv420p,trim=duration={dur:.3f},"
                           f"setpts=PTS-STARTPTS[v{i}]")
            extra_overlays.append({"type": "pfc3d_overlay", "at": t, "dur": dur})
        else:
            dur = item["dur"]
            path = os.path.join(work, f"{item['type']}_{name}_{dur:.2f}.mp4")
            render_gfx(item["type"], dur, path, logo, **item.get("args", {}))
            idx = add_input("-i", path)
            filters.append(f"[{idx}:v]setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
        vlabels.append(f"[v{i}]")
        t += dur
        joins.append(t)
    total = t
    filters.append("".join(vlabels) + f"concat=n={len(vlabels)}:v=1:a=0[base]")

    # ---- picture: overlays ------------------------------------------------
    cur = "base"
    # overlays may be placed by source time ("src_at") instead of timeline time
    src_map, acc = [], 0.0
    for item in tl["sequence"]:
        d = item["out"] - item["in"] if item["type"] == "src" else item["dur"]
        if item["type"] == "src":
            src_map.append((item["in"], item["out"], acc))
        acc += d
    overlays = list(extra_overlays)
    for ov in tl.get("overlays", []):
        ov = dict(ov)
        if "src_at" in ov:
            for a, b, start in src_map:
                if a <= ov["src_at"] < b:
                    ov["at"] = start + ov["src_at"] - a
                    break
            else:
                raise ValueError(f"src_at {ov['src_at']} not in any source segment")
        overlays.append(ov)
    # branded wipe centred on the joins that ask for it
    for j in tl.get("wipe_after", []):
        overlays.append({"type": "wipe", "at": joins[j] - 0.55, "dur": 1.1})
    for k, ov in enumerate(overlays):
        path = os.path.join(work, f"ov_{name}_{k}_{ov['type']}.mov")
        if os.path.exists(path):
            os.remove(path)  # overlays are cheap; always re-render so edits show
        render_gfx(ov["type"], ov["dur"], path, logo, **ov.get("args", {}))
        idx = add_input("-i", path)
        nxt = f"o{k}"
        filters.append(f"[{idx}:v]setpts=PTS-STARTPTS+{ov['at']:.3f}/TB[g{k}]")
        filters.append(f"[{cur}][g{k}]overlay=0:0:eof_action=pass:format=auto[{nxt}]")
        cur = nxt
    filters.append(f"[{cur}]format=yuv420p[vout]")

    # ---- audio: original track, continuous --------------------------------
    aidx = add_input("-i", src)
    filters.append(audio_chain(f"{aidx}:a", tl.get("audio_start", 0.0), total,
                               probe_duration(src, "a"), "aout"))

    graph = os.path.join(work, f"graph_{name}.txt")
    with open(graph, "w") as f:
        f.write(";\n".join(filters))
    run(["ffmpeg", "-y", "-hide_banner", "-stats", "-v", "warning", *inputs,
         "-filter_complex_script", graph, "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
         "-profile:v", "high", "-level", "5.1", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-t", f"{total:.3f}", out])
    print(f"done: {out}  ({total:.2f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline", choices=sorted(TIMELINES))
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default="work")
    assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    default_logo = os.path.join(assets, "logo.png")
    if not os.path.exists(default_logo):  # fallback: logo rebuilt from the source intro
        default_logo = os.path.join(assets, "logo_reverse.png")
    ap.add_argument("--logo", default=default_logo)
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--frames3d", default=None, help="PNG frames from pfc3d.py")
    a = ap.parse_args()
    build(a.timeline, a.src, a.out, a.work, a.logo, a.crf, a.preset, a.frames3d)


if __name__ == "__main__":
    main()
