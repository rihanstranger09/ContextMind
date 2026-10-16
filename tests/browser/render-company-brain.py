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
NAMES=['01-intro','02-model','03-decision-proof','04-decision-answer','05-owner',
       '06-shortest-path','06-memory','07-freshness','08-public-proof','09-public-activity','10-close']
CLIPS=[MEDIA/'company-narration'/f'{name}.mp3' for name in NAMES]
# Seconds relative to capture start; the browser timeline guards scene ordering.
STARTS=[.7,12,18,31.7,50.3,62.6,74.8,85,109.3,118.2,128]
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
(62.6,68,'A bounded shortest-path tool connects Alice through the API Gateway.'),
(68,74.4,'Alice WORKED_ON the gateway; the gateway DEPENDS_ON the Database Cluster.'),
(74.8,84.7,'Reload: saved investigations, tool steps and evidence traces persist in FalkorDB.'),
(85,93,'An authenticated operator adds a fictional blocker. Re-asking sees the updated graph.'),
(93,102,'After it is resolved, it leaves active blockers. Earlier answer snapshots remain saved.'),
(109.3,118,'The same engine, now on real public data. A native traversal reaches GitHub releases.'),
(118.2,126.3,'Public contributor counts are evidence, not proof of maintainer status. This snapshot is bounded.'),
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
    expected=['intro','model','decision_proof','decision_answer','ownership','shortest_path','memory','before_sync','public_proof','public_activity','close']
    observed=[timeline[key] for key in expected]
    if observed!=sorted(observed): raise SystemExit('Unexpected recording scene order')
    for expected_start,real_start in zip((.7,8.2,17.3,31.6,50.3,62.5,74.7,84.3,109.4,118.1,127.6),observed):
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
