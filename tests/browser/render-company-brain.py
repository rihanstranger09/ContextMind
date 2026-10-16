"""Render the guarded native Company Brain recording with supplied narration.

No media files or secrets are bundled in source; record-company-brain.cjs must
succeed first. Input clips may be re-recorded; timings are checked before mix.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MEDIA=ROOT/'deliverables'
VIDEO=MEDIA/'native-company-brain.webm'
TIMELINE=MEDIA/'native-company-brain-timeline.json'
OUTPUT=MEDIA/'contextmind-company-brain-final.mp4'
CAPTIONS=MEDIA/'contextmind-company-brain-final.srt'
NAMES=['intro','model','decision-proof','decision-answer','owner','memory','freshness','public-proof','public-activity','close']
CLIPS=[MEDIA/'company-narration'/f'{i:02d}-{name}.mp3' for i,name in enumerate(NAMES,1)]
# Seconds relative to capture start; the browser timeline guards scene ordering.
STARTS=[.7,12,18,31.7,50.3,63,75,97.2,113,128]
CUES=[
(0.7,7.8,'Company knowledge is scattered. ContextMind connects people, tickets, chats, and decisions behind an answer.'),
(7.8,12,'This demo runs on a real local FalkorDB instance.'),
(12,17.8,'The data model connects decisions to tickets, messages, meetings and documents.'),
(18,25,'A second fixed, parameterized Cypher query runs directly on FalkorDB.'),
(25,31,'The fictional migration decision links to four source types and its impacted project.'),
(31.7,39,'Why was Analytics Migration delayed? The agent selects a decision tool.'),
(39,46,'Open Tools used, the stored paths, and the underlying source records.'),
(50.3,57,'Who owns the Database Cluster? Ownership is grounded in graph relationships.'),
(57,62,'Always confirm the proposed responder’s current availability.'),
(63,72.8,'Reload: saved investigations, tool steps and evidence traces persist in FalkorDB.'),
(75,83,'An authenticated operator adds a fictional blocker. Re-asking sees the updated graph.'),
(83,91.5,'After it is resolved, it leaves active blockers. Earlier answer snapshots remain saved.'),
(97.2,104,'The separate public workspace uses another native Cypher traversal.'),
(104,112,'The organization, Python client and releases link to public GitHub artifacts.'),
(113,120,'Public contributor activity is evidence, not proof of maintainer status.'),
(120,127.7,'This snapshot is bounded, not a live feed or a private company dataset.'),
(128,139.5,'ContextMind · Company Brain. Repository and full local setup in README; no cloud deployment is claimed.')]


def binary():
    if os.getenv('FFMPEG'): return os.environ['FFMPEG']
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        executable=shutil.which('ffmpeg')
        if executable: return executable
        raise SystemExit('Install ffmpeg or set FFMPEG to its executable path.') from None


def duration(ffmpeg,path):
    result=subprocess.run([ffmpeg,'-hide_banner','-i',str(path)],capture_output=True,text=True)
    match=re.search(r'Duration: (\d+):(\d+):([\d.]+)',result.stderr)
    if not match: raise SystemExit(f'Cannot read media duration: {path.name}')
    return int(match[1])*3600+int(match[2])*60+float(match[3])


def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def render():
    for file in [VIDEO,TIMELINE,*CLIPS]:
        if not file.is_file(): raise SystemExit(f'Missing media: {file.name}. Record native footage and supply narration first.')
    timeline=json.loads(TIMELINE.read_text())
    expected=['intro','model','decision_proof','decision_answer','ownership','memory','before_sync','public_proof','public_activity','close']
    observed=[timeline[key] for key in expected]
    if observed!=sorted(observed): raise SystemExit('Unexpected recording scene order')
    for expected_start,real_start in zip((.7,8.2,17.3,31.6,50.3,63,72.6,97.6,112.2,127.7),observed):
        if abs(real_start-expected_start)>4:
            raise SystemExit('Recording scene timing changed; review/re-time narration instead of mislabeling footage')
    ffmpeg=binary()
    if duration(ffmpeg,VIDEO)<139.5: raise SystemExit('Recording is too short for the narrated ending')
    for i,clip in enumerate(CLIPS):
        end=STARTS[i+1] if i+1<len(STARTS) else 140
        if STARTS[i]+duration(ffmpeg,clip)>end+.5:
            raise SystemExit(f'{clip.name} overruns its scene; shorten narration or retime explicitly')
    CAPTIONS.write_text(''.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n' for i,(a,b,text) in enumerate(CUES,1)),encoding='utf-8')
    delayed=''.join(f'[{i+1}:a]adelay={int(s*1000)}|{int(s*1000)}[a{i}];' for i,s in enumerate(STARTS))
    audio=''.join(f'[a{i}]' for i in range(len(CLIPS)))
    filters=delayed+f'{audio}amix=inputs={len(CLIPS)}:duration=longest:normalize=0,alimiter=limit=0.95[aout]'
    style='FontName=DejaVu Sans,FontSize=9,PrimaryColour=&H00FFFFFF,BackColour=&H90000000,BorderStyle=3,Alignment=2,MarginV=8'
    command=[ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(VIDEO)]
    for clip in CLIPS: command+=['-i',str(clip)]
    command+=['-filter_complex',filters,'-vf',f"subtitles='{CAPTIONS}':force_style='{style}'",
              '-map','0:v:0','-map','[aout]','-t','140',
              '-c:v','libx264','-preset','medium','-b:v','1800k','-minrate','1200k','-maxrate','2400k','-bufsize','4800k',
              '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(OUTPUT)]
    subprocess.run(command,cwd=ROOT,check=True)
    print(f'Company Brain video: {OUTPUT}\nCaptions: {CAPTIONS}')


if __name__=='__main__': render()
