import subprocess
import tempfile
import urllib.request
from pathlib import Path

def test_amix():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        vid = tdp / "vid.mp4"
        nar = tdp / "nar.wav"
        mus = tdp / "mus.wav"
        out = tdp / "out.mp4"
        out2 = tdp / "out2.mp4"

        # 10s video
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=10", "-c:v", "libx264", str(vid)], check=True, capture_output=True)
        # 5s speech
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=440:d=5", str(nar)], check=True, capture_output=True)
        # 5s music
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=880:d=5", str(mus)], check=True, capture_output=True)

        vid_dur = 10.0

        # Try current mix cmd
        cmd = [
            "ffmpeg", "-y",
            "-i", str(vid),
            "-i", str(nar),
            "-i", str(mus),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-filter_complex", (
                f"[1:a]volume=1.0,atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS[narrator];"
                f"[2:a]aloop=loop=-1:size=2e+09,volume=0.15,atrim=0:{vid_dur:.3f}[music];"
                "[narrator][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
            ),
            "-map", "0:v", "-map", "[a]",
            "-t", f"{vid_dur:.3f}",
            str(out),
        ]
        res = subprocess.run(cmd, capture_output=True)
        print("MIX1 RETURN:", res.returncode)
        print("MIX1 STDERR:", res.stderr.decode()[-500:])

        # Try safer mix cmd
        cmd2 = [
            "ffmpeg", "-y",
            "-i", str(vid),
            "-i", str(nar),
            "-i", str(mus),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-filter_complex", (
                f"[1:a]volume=1.0,atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS[narrator];"
                f"[2:a]aloop=loop=-1:size=2e+09,volume=0.15,atrim=0:{vid_dur:.3f}[music];"
                "[narrator][music]amix=inputs=2:duration=longest[a]"
            ),
            "-map", "0:v", "-map", "[a]",
            "-t", f"{vid_dur:.3f}",
            str(out2),
        ]
        res2 = subprocess.run(cmd2, capture_output=True)
        print("MIX2 RETURN:", res2.returncode)
        
        # Check lengths
        for p in [out, out2]:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            print(f"{p.name} len:", proc.stdout.strip())

if __name__ == "__main__":
    test_amix()
