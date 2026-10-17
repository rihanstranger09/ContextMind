"""Guarded native v4 render from measured browser take and selected narration.

The MP4 remains under ignored deliverables/, never in Git. Verifies native-only
recording output, timing, speech clip lengths, codec/bitrate, and full decode.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/'deliverables'
VIDEO=MEDIA/'native-company-v4.webm'
TIMELINE=MEDIA/'native-company-v4-timeline.json'
OUTPUT=MEDIA/'ContextMind-v4-native.mp4'
AUDIO=MEDIA/'v4-voiceover.wav'
SRT=MEDIA/'ContextMind-v4-reviewed.srt'
VOICE=ROOT/'scripts/narration-v4'
NAMES=['01-intro','02-model','03-proof','04-router','05-owner','06-impact','07-shortest',
       '08-memory','09-freshness','10-public-close']
STARTS=[0,6,14,26,39,45,64,74,81,97]
KEYS=['intro','model','decision_proof','decision_answer','ownership','impact','shortest',
      'memory','before','public_proof','architecture','close']
EXPECTED=[0,6,14,26,39,45,64,74,81,97,105,113]

def ffmpeg():
    if os.getenv('FFMPEG'): return os.environ['FFMPEG']
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        f=shutil.which('ffmpeg')
        if not f: raise SystemExit('ffmpeg/imageio-ffmpeg required')
        return f

def meta(ff,path):
    r=subprocess.run([ff,'-hide_banner','-i',str(path)],capture_output=True,text=True)
    t=r.stderr
    d=re.search(r'Duration: (\d+):(\d+):([\d.]+)',t)
    if not d: raise SystemExit('Media duration missing: '+path.name)
    return int(d[1])*3600+int(d[2])*60+float(d[3]),t

def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def render():
    clips=[VOICE/(name+'.mp3') for name in NAMES]
    for f in [VIDEO,TIMELINE,*clips]:
        if not f.is_file(): raise SystemExit('Missing native video, timeline or voice asset: '+f.name)
    marks=json.loads(TIMELINE.read_text())
    for key,target in zip(KEYS,EXPECTED):
        if key not in marks or abs(marks[key]-target)>3:
            raise SystemExit(f'Video scene {key} is missing/misaligned; re-record')
    ff=ffmpeg();length,_=meta(ff,VIDEO)
    # Playwright WebM can contain encoder tail after the controlled 120-second take.
    if not 119.5<=length<=135: raise SystemExit(f'Unexpected raw recording length {length}; do not render')
    durations=[meta(ff,p)[0] for p in clips]
    for i,(start,duration) in enumerate(zip(STARTS,durations)):
        end=STARTS[i+1] if i+1<len(STARTS) else 120
        if start+duration>end+.1: raise SystemExit(f'Narration overrun in {clips[i].name}: {duration:.2f}s for {end-start}s scene')
    # Captions are verbatim script text. Durations for composite clips are
    # apportioned by words; review and adjust against speech before submitting.
    sys.path.insert(0,str(ROOT/'scripts'))
    from generate_v4_captions import cues,render as caption_render
    beats=cues(); reviewed=[]
    for i,(start,end,text) in enumerate(beats):
        if i<8:
            actual_end=min(end,start+durations[i]+.05)
            reviewed.append((start,actual_end,text))
        elif i<13:
            # Short operator cues remain on the exact claimed state boundaries.
            reviewed.append((start,end,text))
        else:
            reviewed.append((start,end,text))
    SRT.write_text(caption_render(reviewed),encoding='utf-8')
    # Join exact same-speaker clips at their measured scene starts. Never use a
    # silent placeholder or an audio track from the older v3 recording.
    cmd=[ff,'-y','-hide_banner','-loglevel','error']
    for clip in clips: cmd+=['-i',str(clip)]
    delay=''.join(f'[{i}:a]adelay={start*1000}|{start*1000}[d{i}];' for i,start in enumerate(STARTS))
    inputs=''.join(f'[d{i}]' for i in range(len(clips)))
    cmd+=['-filter_complex',delay+inputs+'amix=inputs=10:duration=longest:normalize=0,apad,atrim=0:120,alimiter=limit=0.95[a]',
          '-map','[a]','-t','120','-c:a','pcm_s16le',str(AUDIO)]
    subprocess.run(cmd,check=True)
    style='FontName=DejaVu Sans,FontSize=19,PrimaryColour=&H00FFFFFF,BackColour=&H90000000,BorderStyle=3,Alignment=2,MarginV=16'
    command=[ff,'-y','-hide_banner','-loglevel','error','-i',str(VIDEO),'-i',str(AUDIO),
       '-vf',f"tpad=stop_mode=clone:stop_duration=1,subtitles='{SRT}':force_style='{style}'",
       '-map','0:v:0','-map','1:a:0','-t','120','-c:v','libx264','-preset','medium',
       '-b:v','3000k','-minrate','3000k','-maxrate','3000k','-bufsize','6000k',
       '-x264-params','nal-hrd=cbr:filler=1','-pix_fmt','yuv420p',
       '-c:a','aac','-b:a','160k','-movflags','+faststart',str(OUTPUT)]
    subprocess.run(command,check=True)
    d,streams=meta(ff,OUTPUT)
    if not 119.5<=d<=120.5 or '1440x900' not in streams or 'Video: h264' not in streams or 'Audio: aac' not in streams:
        raise SystemExit('Output duration, video size, H.264 or AAC failed verification')
    bitrate=re.search(r'Video: h264[^\n]*?(\d+) kb/s',streams)
    if not bitrate or int(bitrate[1])<2000: raise SystemExit('Output video stream under 2 Mbps')
    decode=subprocess.run([ff,'-v','error','-i',str(OUTPUT),'-f','null','-'],capture_output=True,text=True)
    if decode.returncode or decode.stderr: raise SystemExit('Decode failed: '+decode.stderr[:200])
    black=subprocess.run([ff,'-hide_banner','-loglevel','info','-i',str(OUTPUT),
        '-vf','blackdetect=d=0.04:pix_th=0.10','-an','-f','null','-'],capture_output=True,text=True)
    if black.returncode or 'black_start:' in black.stderr: raise SystemExit('Black frames/sections detected; inspect and re-edit')
    print(f'Native v4 candidate: {OUTPUT}\nDuration {d:.2f}s, video {bitrate[1]}kb/s, 1440x900 H.264 + AAC; no black sections; full decode passed.\nCaptions: {SRT}')

if __name__=='__main__': render()
