"""Refresh the profile's GitHub cards from public GitHub data. Python stdlib only."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import json
import os
import re

USER = 'Vizzaq23'
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
GOLD, WHITE, MUTED, CYAN = '#d7b877', '#e8e5da', '#98a5b6', '#85cfe8'
COLORS = ['#1c2531','#514936','#847047','#b6995e','#e1c387']

def fetch(url):
    headers={'User-Agent':'Vizzaq23-profile','Accept':'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'text/html'}
    token=os.environ.get('GITHUB_TOKEN')
    if token and url.startswith('https://api.github.com/'):
        headers['Authorization']='Bearer '+token
    with urlopen(Request(url,headers=headers),timeout=40) as r:
        data=r.read().decode('utf-8')
    return json.loads(data) if url.startswith('https://api.github.com/') else data

class Calendar(HTMLParser):
    def __init__(self):
        super().__init__();self.cells={};self.tips={};self.target=None;self.buffer=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'data-date' in a and 'data-level' in a:
            self.cells[a['id']]=(a['data-date'],int(a['data-level']))
        if tag=='tool-tip':self.target=a.get('for');self.buffer=[]
    def handle_data(self,text):
        if self.target:self.buffer.append(text)
    def handle_endtag(self,tag):
        if tag=='tool-tip' and self.target:
            self.tips[self.target]=''.join(self.buffer).strip();self.target=None

def parse_calendar(source):
    p=Calendar();p.feed(source)
    result=[]
    if not p.cells:raise ValueError('GitHub calendar markup is missing; keeping prior assets.')
    for ident,(day,level) in p.cells.items():
        tip=p.tips.get(ident,'')
        m=re.match(r'(No|[\d,]+) contributions? on ',tip)
        if not m:raise ValueError('Missing contribution count for '+day)
        count=0 if m[1]=='No' else int(m[1].replace(',',''))
        result.append((day,count,level))
    return sorted(result)

def streaks(days,today):
    counts={date.fromisoformat(d):c for d,c,_ in days}
    cursor=today if counts.get(today,0) else today-timedelta(days=1)
    current=0
    while counts.get(cursor,0)>0:
        current+=1;cursor-=timedelta(days=1)
    longest=run=0;previous=None
    for day,count,_ in days:
        d=date.fromisoformat(day)
        if previous is not None and d!=previous+timedelta(days=1):run=0
        run=run+1 if count else 0
        longest=max(longest,run);previous=d
    return current,longest

def txt(x,y,text,size=14,color=WHITE,extra=''):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{escape(str(text))}</text>'

def svg(title,body,w=1000,h=260):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title,quote=True)}"><title>{escape(title)}</title><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="4" fill="#0f1620" stroke="#303c4b"/><g font-family="Segoe UI,Arial,sans-serif">{body}</g></svg>'''

def render(data):
    days=data['days'];profile=data['profile'];repos=data['repos'];langs=data['languages'];stamp=data['updated']
    total=sum(c for _,c,_ in days);current,longest=streaks(days,date.fromisoformat(stamp))
    foot=txt(24,238,'PUBLIC DATA · '+stamp,11,MUTED)
    body=txt(24,34,'GITHUB STATS',14,GOLD, 'letter-spacing="2"')
    metrics=[('Repositories',profile['public_repos']),('Stars',sum(r['stargazers_count'] for r in repos)),('Followers',profile['followers']),('Contributions · last year',total)]
    for i,(label,value) in enumerate(metrics):
        x=24+(i%2)*244;y=89+(i//2)*79
        body+=txt(x,y,f'{value:,}',33)+txt(x,y+23,label,12,MUTED)
    cards={'github-stats.svg':svg('Public GitHub stats',body+foot,500)}
    body=txt(24,34,'CONTRIBUTION STREAK',14,GOLD,'letter-spacing="2"')
    body+='<circle cx="130" cy="120" r="57" fill="none" stroke="#514936" stroke-width="2"/>'
    body+=txt(130,131,current,42,GOLD,'text-anchor="middle"')+txt(130,155,'CURRENT',10,MUTED,'text-anchor="middle"')
    body+=txt(244,105,str(longest)+' days',30)+txt(244,132,'Longest in this calendar',13,MUTED)
    body+=txt(244,174,str(sum(c>0 for _,c,_ in days))+' active days',19,CYAN)
    cards['github-streak.svg']=svg('Contribution streak in the displayed calendar',body+foot,500)
    top=sorted(langs.items(),key=lambda x:x[1],reverse=True)[:8];den=sum(langs.values()) or 1
    body=txt(24,35,'LANGUAGES',14,GOLD,'letter-spacing="2"')
    palette=[GOLD,CYAN,'#b8a1e3','#9fc9a2','#db9679','#739be0','#cebda4','#abbdc7']
    for i,(name,count) in enumerate(top):
        x=24+(i%2)*500;y=76+(i//2)*49;pct=count/den*100
        body+=txt(x,y,name,14)+txt(x+439,y,f'{pct:.1f}%',12,MUTED,'text-anchor="end"')
        body+=f'<rect x="{x}" y="{y+9}" width="440" height="5" rx="2" fill="#27313e"/><rect x="{x}" y="{y+9}" width="{440*pct/100:.2f}" height="5" rx="2" fill="{palette[i]}"/>'
    body+=txt(24,291,'BY GITHUB-REPORTED BYTES · PUBLIC NON-FORK REPOSITORIES · '+stamp,11,MUTED)
    cards['github-languages.svg']=svg('Languages by public repository bytes',body,h=314)
    recent=days[-90:];maxc=max(1,max(c for _,c,_ in recent));points=[]
    body=txt(24,35,'ACTIVITY / LAST 90 DAYS',14,GOLD,'letter-spacing="2"')
    for i,(d,c,_) in enumerate(recent):points.append(f'{48+i*904/max(1,len(recent)-1):.2f},{201-c/maxc*132:.2f}')
    body+='<path d="M48 69H952 M48 135H952 M48 201H952" stroke="#263240" fill="none"/>'
    body+=txt(20,73,maxc,10,MUTED)+txt(25,204,'0',10,MUTED)
    body+=f'<polygon points="48,201 {" ".join(points)} 952,201" fill="#d7b877" opacity=".10"/><polyline points="{" ".join(points)}" fill="none" stroke="{GOLD}" stroke-width="2"/>'
    body+=txt(48,233,recent[0][0],12,MUTED)+txt(952,233,recent[-1][0],12,MUTED,'text-anchor="end"')
    cards['github-activity.svg']=svg('Daily GitHub contributions for the last 90 days',body)
    milestones=[('FIRST REPO',profile['public_repos']>=1,'Created a public repo'),('100 CONTRIBUTIONS',total>=100,'In this calendar'),('3 LANGUAGES',len(langs)>=3,'In public repositories'),('10 REPOSITORIES',profile['public_repos']>=10,'Public repositories')]
    body=txt(24,34,'MILESTONES',14,GOLD,'letter-spacing="2"')
    for i,(label,unlocked,sub) in enumerate(milestones):
        x=125+i*250;col=GOLD if unlocked else MUTED
        body+=f'<path d="M{x-14} 65H{x+14}V81Q{x+14} 99 {x} 99Q{x-14} 99 {x-14} 81Z M{x-14} 70H{x-23}V78Q{x-23} 90 {x-11} 90 M{x+14} 70H{x+23}V78Q{x+23} 90 {x+11} 90 M{x} 99V112 M{x-11} 112H{x+11}" fill="none" stroke="{col}" stroke-width="2"/>'
        body+=txt(x,141,label,12,col,'text-anchor="middle"')+txt(x,164,sub,11,MUTED,'text-anchor="middle"')+txt(x,187,'UNLOCKED' if unlocked else 'IN PROGRESS',10,col,'text-anchor="middle"')
    cards['github-trophies.svg']=svg('Custom GitHub milestones, not official GitHub achievements',body,h=210)
    # A continuous snake sweeps the real contribution cells, dimming each visited cell.
    first=date.fromisoformat(days[0][0]);sunday=first-timedelta(days=(first.weekday()+1)%7)
    cells=[]
    for day,count,level in days:
        delta=(date.fromisoformat(day)-sunday).days;col,row=divmod(delta,7)
        cells.append((col,row,count,level,day))
    cols=max(c[0] for c in cells)+1;step=min(17,920/max(cols,1));offset=(1000-cols*step)/2
    traversal=[(col,row) for col in range(cols) for row in (range(7) if col%2==0 else range(6,-1,-1))]
    index={v:i for i,v in enumerate(traversal)};n=len(traversal)
    body=txt(24,33,'CONTRIBUTION SNAKE',14,GOLD,'letter-spacing="2"')
    styles=['@media(prefers-reduced-motion:reduce){.cell{animation:none!important}.snake{display:none}}']
    for col,row,count,level,day in cells:
        p=(index[(col,row)]+1)/n*90
        styles.append(f'@keyframes c{col}r{row}{{0%,{max(0,p-.1):.3f}%{{opacity:1}}{p:.3f}%,94%{{opacity:.18}}100%{{opacity:1}}}}')
        body+=f'<rect class="cell" x="{offset+col*step:.2f}" y="{60+row*step:.2f}" width="{step-3:.2f}" height="{step-3:.2f}" rx="2" fill="{COLORS[level]}" style="animation:c{col}r{row} 30s linear infinite"><title>{day}: {count} contributions</title></rect>'
    route='M'+' L'.join(f'{offset+c*step+(step-3)/2:.2f} {60+r*step+(step-3)/2:.2f}' for c,r in traversal)
    for i in range(4):
        body+=f'<circle class="snake" r="{(step-2)/2:.2f}" fill="{GOLD}" opacity="{1-i*.16}"><animateMotion dur="30s" repeatCount="indefinite" begin="{i*.06}s" path="{route}" keyPoints="0;1;1" keyTimes="0;0.9;1" calcMode="linear"/></circle>'
    body+=txt(24,218,'PUBLIC CONTRIBUTION CALENDAR · '+stamp,11,MUTED)
    cards['github-snake.svg']=svg('Animated snake over the public contribution calendar','<style>'+''.join(styles)+'</style>'+body,h=240)
    return cards

def collect():
    profile=fetch(f'https://api.github.com/users/{USER}')
    repos=[];page=1
    while True:
        batch=fetch(f'https://api.github.com/users/{USER}/repos?per_page=100&page={page}')
        repos.extend(batch)
        if len(batch)<100:break
        page+=1
    languages=Counter()
    for repo in repos:
        if not repo['fork']:
            languages.update(fetch(repo['languages_url']))
    days=parse_calendar(fetch(f'https://github.com/users/{USER}/contributions'))
    today=datetime.now(timezone.utc).date()
    days=[d for d in days if date.fromisoformat(d[0])<=today]
    if len(days)<300 or date.fromisoformat(days[-1][0])!=today:
        raise ValueError('Calendar incomplete or stale; keeping prior assets.')
    if any(date.fromisoformat(b[0])-date.fromisoformat(a[0])!=timedelta(days=1) for a,b in zip(days,days[1:])):
        raise ValueError('Calendar has gaps; keeping prior assets.')
    return {'updated':today.isoformat(),'profile':{k:profile[k] for k in ('login','public_repos','followers')},'repos':[{'name':r['name'],'stargazers_count':r['stargazers_count']} for r in repos],'languages':dict(languages),'days':days}

def main():
    data=collect();cards=render(data)
    # Collect and render everything first: network failures do not replace prior cards.
    ASSETS.mkdir(exist_ok=True)
    for name,content in cards.items():(ASSETS/name).write_text(content,encoding='utf-8')
    (ASSETS/'github-data.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(f'Updated {len(cards)} cards for {USER}; {len(data["days"])} calendar days; {len(data["languages"])} languages.')

if __name__=='__main__':main()
