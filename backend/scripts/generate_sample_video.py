
import subprocess
import sys
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "media" / "sample" / "checkpoint.mp4"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    filter_complex = (
        "testsrc2=size=640x360:rate=15[bg];"
        "[bg]drawbox=x=0:y=280:w=640:h=80:color=black@0.55:t=fill[boxed];"
        "[boxed]drawtext=text='C002 - Gandhinagar RTO Checkpoint':"
        "x=10:y=295:fontsize=16:fontcolor=white,"
        "drawtext=text='%{localtime\\:%Y-%m-%d %H\\\\\\:%M\\\\\\:%S}':"
        "x=10:y=318:fontsize=14:fontcolor=0x00e678"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filter_complex,
        "-t", "20",
        "-pix_fmt", "yuv420p",
        str(OUT_PATH),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("ffmpeg failed to generate the sample clip")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
