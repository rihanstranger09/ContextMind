"""Mix five narration clips into the guarded native browser recording.

Requires ffmpeg (FFMPEG=/path/to/ffmpeg) and separately supplied narration
clips. The script never creates or fakes graph footage. Outputs are gitignored.
Run from any directory: python tests/browser/render-showcase.py
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DELIVERABLES = ROOT / 'deliverables'
VIDEO = DELIVERABLES / 'native-falkordb-showcase.webm'
OUTPUT = DELIVERABLES / 'contextmind-falkordb-presenting-video.mp4'
CAPTIONS = DELIVERABLES / 'contextmind-falkordb-presenting-video.srt'
CLIPS = [DELIVERABLES / 'narration' / f'{i:02d}-{name}.mp3' for i, name in enumerate(
    ('intro', 'proof', 'question', 'trace', 'boundary'), 1)]
STARTS = (0, 16, 39, 57, 75)  # seconds; match the holds in record-showcase.cjs
# Caption text mirrors the narration rather than adding unsupported claims.
CUES = [
    (0, 7, 'ContextMind is an evidence-first company brain.'),
    (7, 15, "Today, we're using a public FalkorDB GitHub snapshot on a native FalkorDB backend,\nnot a JSON mock. The status indicator verifies that the database is running."),
    (16, 24, 'Now I open the FalkorDB proof. This fixed, parameterized Cypher query\nruns on the graph itself.'),
    (24, 31, 'It traverses from the FalkorDB organisation, through the Python client repository,\nto recorded releases.'),
    (31, 37, 'The panel shows stored entity and relationship counts,\nwith links to the original release pages.'),
    (39, 47, 'Next, I ask how to use FalkorDB with LangChain. ContextMind returns a bounded,\nsource-backed answer, with documentation and repository evidence.'),
    (47, 56, "It isn't inventing the connection: each factual statement\ncan be followed back to the graph."),
    (57, 64, 'Open a source card, then expand why this answer.\nThe citation leads to a GitHub artifact.'),
    (64, 72, 'The trace shows the relationships used to retrieve it.\nFalkorDB is doing the retrieval, not merely drawing a diagram.'),
    (75, 84, "Finally, ask for FalkorDB's annual revenue. That figure is not in\nthis public snapshot, so ContextMind refuses to invent it."),
    (84, 95, 'This dataset is a captured slice of public GitHub activity, not a live feed;\nthe assistant uses deterministic graph evidence, not a language model.'),
]


def ffmpeg_binary():
    if os.getenv('FFMPEG'):
        return os.environ['FFMPEG']
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        executable = shutil.which('ffmpeg')
        if executable:
            return executable
        raise SystemExit('Install ffmpeg or set FFMPEG to its executable path.') from None


def duration(binary, path):
    result = subprocess.run([binary, '-hide_banner', '-i', str(path)],
                            capture_output=True, text=True)
    match = re.search(r'Duration: (\d+):(\d+):([\d.]+)', result.stderr)
    if not match:
        raise SystemExit(f'Cannot read duration: {path.name}')
    return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])


def stamp(seconds):
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d},000'


def render():
    for file in [VIDEO, *CLIPS]:
        if not file.is_file():
            raise SystemExit(f'Missing media: {file}. Record the native browser take and add narration clips first.')
    binary = ffmpeg_binary()
    video_length = duration(binary, VIDEO)
    if not 94 <= video_length <= 110:
        raise SystemExit(f'Unexpected video duration ({video_length:.1f}s); rerun the current native recording script.')
    for i, clip in enumerate(CLIPS):
        end = STARTS[i + 1] if i + 1 < len(STARTS) else video_length
        if STARTS[i] + duration(binary, clip) > end + .15:
            raise SystemExit(f'Narration {clip.name} overlaps the next scene; shorten it before rendering.')
    CAPTIONS.write_text(''.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n'
                                for i, (a, b, text) in enumerate(CUES, 1)), encoding='utf-8')
    delayed = ''.join(f'[{i + 1}:a]adelay={start * 1000}|{start * 1000}[a{i}];'
                      for i, start in enumerate(STARTS))
    audio = ''.join(f'[a{i}]' for i in range(len(CLIPS)))
    filters = delayed + f'{audio}amix=inputs=5:duration=longest:normalize=0,alimiter=limit=0.95[aout]'
    style = 'FontName=DejaVu Sans,FontSize=9,PrimaryColour=&H00FFFFFF,BackColour=&H90000000,BorderStyle=3,Alignment=2,MarginV=8'
    command = [binary, '-y', '-hide_banner', '-loglevel', 'error', '-i', str(VIDEO)]
    for clip in CLIPS:
        command += ['-i', str(clip)]
    command += ['-filter_complex', filters,
                '-vf', f"subtitles='{CAPTIONS}':force_style='{style}'",
                '-map', '0:v:0', '-map', '[aout]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(OUTPUT)]
    subprocess.run(command, cwd=ROOT, check=True)
    print(f'Native FalkorDB presentation: {OUTPUT}\nCaptions: {CAPTIONS}')


if __name__ == '__main__':
    render()
