"""Generate draft SRT with every quoted script line verbatim.

Optional --timings JSON maps 1-based cue numbers to measured [start,end] seconds.
Timing overrides never change the spoken/caption text. Listen to the final mix
before treating this draft as synchronized subtitles.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'docs/company-brain-v4-script.md'
DEFAULT = ROOT / 'presentation/ContextMind-v4-draft.srt'
ROW = re.compile(r'^\|\s*(\d:\d\d)–(\d:\d\d)\s*\|.*?\|\s*“([^”]+)”\s*\|\s*$')


def seconds(stamp):
    minutes, remainder = stamp.split(':')
    return int(minutes) * 60 + int(remainder)


def stamp(value):
    millis = round(value * 1000)
    return f'{millis//3600000:02d}:{millis//60000%60:02d}:{millis//1000%60:02d},{millis%1000:03d}'


def cues(script=SCRIPT, timings=None):
    rows = []
    for line in Path(script).read_text(encoding='utf-8').splitlines():
        match = ROW.match(line)
        if match:
            start, end, text = match.groups()
            rows.append((seconds(start), seconds(end), text))
    if len(rows) != 16 or rows[0][0] != 0 or rows[-1][1] > 130:
        raise ValueError('Expected sixteen v4 beats, starting at zero and ending by 2:10')
    overrides = json.loads(Path(timings).read_text()) if timings else {}
    result=[]
    for i, (start,end,text) in enumerate(rows,1):
        if str(i) in overrides:
            start,end=overrides[str(i)]
        if not (isinstance(start,(float,int)) and isinstance(end,(float,int)) and 0<=start<end<=130):
            raise ValueError(f'Invalid cue {i} timing')
        if result and start < result[-1][1]:
            raise ValueError(f'Overlapping cue {i}')
        result.append((start,end,text))
    return result


def render(rows):
    return ''.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n'
                   for i,(a,b,text) in enumerate(rows,1))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--script',type=Path,default=SCRIPT)
    p.add_argument('--timings',type=Path,help='optional reviewed JSON timing overrides')
    p.add_argument('--output',type=Path,default=DEFAULT)
    args=p.parse_args()
    rows=cues(args.script,args.timings)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(rows),encoding='utf-8')
    print(f'Draft captions: {args.output} ({len(rows)} beats; last end {rows[-1][1]}s)')
