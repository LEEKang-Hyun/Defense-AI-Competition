"""
export_story.py — 한 화면 시연 (demo_story.html) 만들기  (2026-10-18 추가)

왜 따로 만드나
  demo.html(백업 화면)은 분석관 작업대라 아래로 길고, 처음 보는 사람은 어디를 봐야 하는지 모른다.
  이 화면은 "이 프로그램이 무엇을 위해 존재하고 → 어떻게 움직이고 → 어떤 결과를 내고 → 사람은 무엇을 하는가"를
  **스크롤 없이 한 화면**에서 8단계로 진행한다. 왼쪽 단계 레일 · 가운데 무대(그림) · 오른쪽 '지금 보는 것' 설명 · 아래 72시간 스크러버.
  ←/→ 또는 '다음' 버튼, 또는 '자동 재생(약 3분)'. 숫자는 demo.html과 같은 데이터(export_html.build_data)에서 나온다.

실행 : python export_story.py  →  demo_story.html   (인터넷·파이썬 없이 열림)
"""
import json, os

import export_html as EH

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FIMI 서사 조기경보 — 한 화면 시연</title>
<script>/*PLOTLY*/</script>
<style>
:root{--bg:#1b1b1f;--bar-bg:#202026;--panel:#232329;--panel2:#2a2a31;--ink:#e6e6ea;--muted:#9b9ba5;--line:#34343c;--hover:#2a2a31;--track:#34343c;
 --ord:#7fb0ff;--sus:#ff7a45;--src:#2fe3a0;--acc:#a882ff;--acc-ink:#1b1b1f;--A:#b39cff;--B:#2fd1b8;--C:#ff7a45;--D:#7a7a84;
 --kp-bg:#26262d;--quote-bg:#2a2838;--pol-bg:#2f2724;--soft-bg:#232a36;--lim-bg:#2f2a1c;--lim-fg:#e3c36a;--note-bg:#1f2a3a;--note-fg:#9cc4ff;--mono-bg:#1f1f24;--row-hl:#2f2622;
 --g-ord:#8fa6c4;--g-sus:#ff7a45;--g-src:#2fe3a0;--g-edge:200,205,220;--grid:#2c2c33;--plot-font:#d6d6dc}
body.light{--bg:#f4f3ee;--bar-bg:#fbfbf8;--panel:#fff;--panel2:#f6f5f0;--ink:#1f1f1d;--muted:#6b6b66;--line:#e3e2db;--hover:#f6f5f0;--track:#e6e5df;
 --ord:#2a78d6;--sus:#eb6834;--src:#1baf7a;--acc:#1f1f1d;--acc-ink:#fff;--A:#6c4ad6;--B:#0f9d8a;--C:#eb6834;--D:#9a9a94;
 --kp-bg:#fbfbf8;--quote-bg:#faf9ff;--pol-bg:#fff8f4;--soft-bg:#f6f9fe;--lim-bg:#fdf6e3;--lim-fg:#8a6200;--note-bg:#eef4fc;--note-fg:#1c5cab;--mono-bg:#fbfbf8;--row-hl:#fff8f4;
 --g-ord:#6f8fb8;--g-sus:#eb6834;--g-src:#1baf7a;--g-edge:90,95,110;--grid:#eeede7;--plot-font:#1f1f1d}
*{box-sizing:border-box}html,body{height:100%;margin:0;overflow:hidden}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:14px;line-height:1.45;transition:background .25s,color .25s}
.app{display:grid;grid-template-rows:60px minmax(0,1fr) 78px;height:100vh;width:100vw;overflow:hidden}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 22px;border-bottom:1px solid var(--line);background:var(--bar-bg);min-width:0;overflow:hidden}
header .brand{display:flex;align-items:baseline;gap:14px;min-width:0}header .brand b{font-size:17px;white-space:nowrap}header .brand span{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tags{display:flex;gap:6px;align-items:center;flex-shrink:0}.tag{font-size:11.5px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:3px 9px;background:var(--panel);white-space:nowrap}
.btn{padding:6px 11px;border:1px solid var(--line);background:var(--panel2);border-radius:8px;cursor:pointer;font-size:12.5px;color:var(--ink);white-space:nowrap;text-decoration:none}
.btn:hover{border-color:var(--acc)}.btn.pri{background:var(--acc);color:var(--acc-ink);border-color:var(--acc)}.btn:disabled{opacity:.45;cursor:default}
.mid{display:grid;grid-template-columns:236px minmax(0,1fr) 348px;gap:14px;padding:14px 18px;min-height:0}
.rail{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:4px;min-height:0;min-width:0;overflow:hidden}
.rail .hd{font-size:11.5px;color:var(--muted);padding:4px 8px 6px}
.st{display:grid;grid-template-columns:26px 1fr;gap:8px;padding:8px 8px;border-radius:10px;cursor:pointer;border:1px solid transparent;align-items:start}
.st:hover{background:var(--hover)}.st.on{background:var(--acc);color:var(--acc-ink)}.st.done .n{background:var(--src);color:#1b1b1f;border-color:var(--src)}
.st .n{width:24px;height:24px;border-radius:50%;border:1.5px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;background:var(--panel2);color:var(--ink)}
.st.on .n{background:var(--acc-ink);color:var(--acc);border-color:var(--acc-ink)}.st .t{font-size:13.5px;font-weight:700;line-height:1.25}.st .s{font-size:11.5px;color:var(--muted);margin-top:2px}.st.on .s{color:var(--acc-ink);opacity:.75}
.stage{background:var(--panel);border:1px solid var(--line);border-radius:14px;min-height:0;min-width:0;display:grid;grid-template-rows:auto minmax(0,1fr);overflow:hidden}
.shead{display:flex;justify-content:space-between;align-items:flex-end;padding:14px 18px 8px;border-bottom:1px solid var(--line)}
.shead h1{margin:0;font-size:20px;letter-spacing:-.2px}.shead .sub{color:var(--muted);font-size:13px;margin-top:2px}.shead>div:first-child{min-width:0;padding-right:14px}
.shead .clock{text-align:right;font-size:12px;color:var(--muted);white-space:nowrap;flex-shrink:0}.shead .clock b{display:block;font-size:20px;color:var(--ink);font-variant-numeric:tabular-nums}
.sbody{padding:12px 16px 14px;min-height:0;min-width:0;position:relative;overflow:hidden}
.g2{display:grid;grid-template-columns:3fr 2fr;gap:14px;height:100%;min-height:0}.g11{display:grid;grid-template-columns:1fr 1fr;gap:14px;height:100%;min-height:0}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;height:100%;min-height:0}
.box{border:1px solid var(--line);border-radius:12px;background:var(--panel);min-height:0;overflow:hidden;display:flex;flex-direction:column}
.box .bt{font-size:12px;color:var(--muted);padding:8px 12px 0}.box .bc{flex:1;min-height:0;padding:6px 10px 8px;overflow:auto}
.plot{width:100%;height:100%;min-height:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:10px;min-height:0;min-width:0;overflow:auto}
.panel .hd{font-size:11.5px;color:var(--muted);text-transform:none}.panel h2{margin:0;font-size:16px}
.kp{border:1px solid var(--line);border-radius:12px;padding:9px 12px;background:var(--kp-bg)}.kp .l{font-size:11.5px;color:var(--muted)}.kp .v{font-size:24px;font-weight:700;letter-spacing:-.3px;font-variant-numeric:tabular-nums;margin-top:1px}.kp .v small{font-size:12px;color:var(--muted);font-weight:400;margin-left:6px}.kp .n{font-size:11.5px;color:var(--muted);margin-top:2px}
.mean{font-size:13.5px}.mean b{color:var(--ink)}.lim{font-size:12px;color:var(--lim-fg);background:var(--lim-bg);border-radius:8px;padding:8px 10px}
.note{font-size:12.5px;color:var(--note-fg);background:var(--note-bg);border-radius:8px;padding:8px 10px;display:none}.show-note .note{display:block}
footer{display:grid;grid-template-columns:1fr auto;gap:18px;align-items:center;padding:0 22px;border-top:1px solid var(--line);background:var(--bar-bg)}
.scrub{position:relative;padding:14px 0 0}.scrub input{width:100%;margin:0;accent-color:var(--acc)}.marks{position:relative;height:18px;font-size:10.5px;color:var(--muted)}
.marks span{position:absolute;transform:translateX(-50%);white-space:nowrap}.marks span::before{content:"";display:block;width:1px;height:5px;background:var(--muted);margin:0 auto 1px}
.ctrl{display:flex;gap:8px;align-items:center}.ctrl .hint{font-size:11px;color:var(--muted);margin-left:6px}
.prog{position:absolute;left:0;top:8px;height:3px;background:var(--track);width:100%;border-radius:2px;overflow:hidden}.prog i{display:block;height:3px;background:var(--acc);width:0}
.pipe{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;align-items:stretch}
.pb{border:1.5px solid var(--line);border-radius:12px;padding:10px 12px;position:relative;background:var(--kp-bg);min-height:118px}
.pb .k{font-size:11px;color:var(--muted)}.pb .t{font-weight:700;font-size:14px;margin:2px 0 4px}.pb .d{font-size:12px;color:var(--muted);line-height:1.35;min-height:48px}.pb .v{font-size:20px;font-weight:700;margin-top:8px;font-variant-numeric:tabular-nums;word-break:keep-all}.pb .v small{display:block;font-size:11.5px;color:var(--muted);font-weight:400;white-space:normal;margin-top:1px}
.pb::after{content:"→";position:absolute;right:-13px;top:46%;color:var(--muted);font-size:15px}.pb:last-child::after{content:""}
.prin{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}
.pr{border-radius:12px;padding:12px 14px;background:var(--kp-bg);border:1px solid var(--line)}.pr b{display:block;font-size:14px;margin-bottom:3px}.pr span{font-size:12.5px;color:var(--muted)}
.big{font-size:38px;font-weight:700;letter-spacing:-.5px;line-height:1.05;font-variant-numeric:tabular-nums}
.lv{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:700;font-size:13px;white-space:nowrap}
.bar{height:9px;background:var(--track);border-radius:5px;margin:3px 0 8px}.bar i{display:block;height:9px;border-radius:5px}
.cmp{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;text-align:center;margin:8px 0}
.cmp .big{font-size:32px}.cmp .vs{color:var(--muted);font-size:12px}
.pol{border-left:3px solid var(--sus);padding:8px 12px;background:var(--pol-bg);border-radius:0 10px 10px 0;margin-top:8px}.pol b{font-size:15px}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{border:1.5px solid var(--line);border-radius:9px;padding:5px 8px;font-size:12px;background:var(--panel2)}
.quote{font-size:13.5px;line-height:1.65;padding:8px 10px;border-left:3px solid var(--A);background:var(--quote-bg);border-radius:0 8px 8px 0;margin:6px 0}
.tbl{width:100%;border-collapse:collapse;font-size:12px}.tbl th,.tbl td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:middle}.tbl th{color:var(--muted);font-weight:600;white-space:nowrap}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;white-space:pre-wrap;line-height:1.5;color:var(--ink);background:var(--mono-bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.fade{animation:fd .35s ease}@keyframes fd{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.lim-list{display:flex;gap:8px;flex-wrap:wrap}.lim-list span{font-size:11.5px;color:var(--lim-fg);background:var(--lim-bg);border-radius:8px;padding:4px 8px}
.cmpw{position:relative;width:100%;aspect-ratio:16/9;background:#000;border-radius:10px;overflow:hidden;border:1px solid var(--line)}
.cmpw img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}.cmpw .after{clip-path:inset(0 0 0 50%)}
.cmpw .div{position:absolute;top:0;bottom:0;width:2px;background:#fff;left:50%;box-shadow:0 0 6px rgba(0,0,0,.6)}
.cmpw .lab{position:absolute;top:8px;font-size:11px;padding:2px 7px;border-radius:6px;background:rgba(0,0,0,.55);color:#fff}.cmpw .lab.l{left:8px}.cmpw .lab.r{right:8px}
.cmpw input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}
.cmpw .ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:14px 18px;font-size:11.5px;line-height:1.55;color:var(--muted);background:var(--kp-bg);overflow:hidden}.cmpw .ph code{display:block;font-size:11px;color:var(--ink);word-break:break-all;margin:4px 0}
.sattabs{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 8px}.sattabs .btn{padding:4px 9px;font-size:11.5px}
.gwrap{position:relative;height:100%;border-radius:12px;overflow:hidden;background:var(--bg);border:1px solid var(--line)}.gwrap canvas{position:absolute;inset:0;width:100%;height:100%;cursor:grab}
.ghud{position:absolute;right:12px;top:12px;background:color-mix(in srgb,var(--panel) 86%,transparent);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:12.5px;line-height:1.7;backdrop-filter:blur(6px);font-variant-numeric:tabular-nums}
.ghud .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}.gnote{position:absolute;left:12px;bottom:10px;font-size:11px;color:var(--muted)}
.gtog{position:absolute;left:12px;top:12px;display:flex;gap:6px}.gtip{position:absolute;pointer-events:none;display:none;font-size:12px;padding:7px 10px;max-width:260px;background:color-mix(in srgb,var(--panel) 92%,transparent);border:1px solid var(--line);border-radius:8px}
@media(max-width:1180px){.mid{grid-template-columns:200px minmax(0,1fr) 300px}.pipe{grid-template-columns:repeat(3,1fr)}.pb::after{content:""}}
</style></head><body>
<div class="app">
<header>
 <div class="brand"><b>FIMI 서사 조기경보</b><span id="purpose">외국발 서사가 시민의 말이 되기 전에, 행동으로 잡고 근거와 함께 권고하는 분석관 보조</span></div>
 <div class="tags"><span class="tag">합성 72시간 시나리오</span><span class="tag">계정·매체 가상 · 가명 ID</span><span class="tag">판정 아님 · 최종 결정은 사람</span>
  <button class="btn" id="themeBtn" title="다크(그래프 뷰) ↔ 라이트">☾</button><button class="btn" id="noteBtn" title="발표 멘트 보기/숨기기">멘트</button><button class="btn" id="fsBtn" title="전체 화면">⛶</button><a class="btn" href="http://localhost:8501" target="_blank" title="분석관 대시보드(시연 시작.command로 켜져 있을 때)">대시보드</a><a class="btn" href="demo.html" target="_blank" title="분석관 상세 화면(오프라인 백업) 새 탭">백업 화면</a></div>
</header>
<div class="mid">
 <nav class="rail" id="rail"></nav>
 <section class="stage"><div class="shead"><div><h1 id="stitle"></h1><div class="sub" id="ssub"></div></div><div class="clock" id="sclock"></div></div><div class="sbody" id="sbody"></div></section>
 <aside class="panel" id="panel"></aside>
</div>
<footer>
 <div class="scrub"><div class="prog" id="prog"><i></i></div><input type="range" id="hs" min="0" max="72" step="1" value="13"><div class="marks" id="marks"></div></div>
 <div class="ctrl"><button class="btn" id="prev">◀ 이전</button><button class="btn pri" id="next">다음 ▶</button><button class="btn" id="play">▶ 자동 재생 (1분)</button><span class="hint">← → 단계 · Space 재생/정지 · 슬라이더 = 관측 시각</span></div>
</footer>
</div>
<script>
const D=/*DATA*/;
// ---------------------------------------------------------------- 공통
const CAMP=String(D.pre?D.pre.summary.campaign_narrative:Object.keys(D.nars)[0]);const N=D.nars[CAMP];
const LV={NONE:["·","#9b9ba5","경보 없음"],REVIEW:["◇","#9b9ba5","검토 권장"],WATCH:["●","#f0b429","관찰"],ALERT:["▲","#ff8a5c","경보"],CRITICAL:["■","#ff5c5c","위험"]};
const cssVar=n=>getComputedStyle(document.body).getPropertyValue(n).trim();
const CC=()=>({ord:cssVar("--ord"),sus:cssVar("--sus"),src:cssVar("--src")}),AXC=()=>({A:cssVar("--A"),B:cssVar("--B"),C:cssVar("--C"),D:cssVar("--D")});
const GRID=()=>cssVar("--grid");
const PST={none:["·","#8a8a85"],watch:["◇","#8a8a85"],rhetoric_only:["◆","#6c4ad6"],partial:["◐","#e0a000"],converged:["●","#d03b3b"],mismatch:["⚡","#8e24aa"]};
const PLVC={NONE:"#5a5a63",REVIEW:"#8a8a94",WATCH:"#f0b429",ALERT:"#ff8a5c",CRITICAL:"#ff5c5c"};
const PF={conditional:["조건부","#6c4ad6"],deadline:["시한","#d03b3b"],place:["장소","#0f9d8a"],means:["수단","#eb6834"],blame:["책임 전가","#8a8a85"],threat:["위협","#b23a48"],announce:["예고 서술어","#7a5c00"],soft:["완화","#2a78d6"]};
const esc=t=>String(t==null?"":t).replace(/&/g,"&amp;").replace(/</g,"&lt;");
const t0=new Date(D.t0.replace(" ","T"));const p2=n=>String(n).padStart(2,"0");
const fmt=h=>{const d=new Date(t0.getTime()+h*3600e3);return `${p2(d.getMonth()+1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`};
const BASE=()=>({paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:{family:"-apple-system,Apple SD Gothic Neo,sans-serif",size:12,color:cssVar("--plot-font")},margin:{l:44,r:12,t:30,b:40}});
const cfg={displayModeBar:false,responsive:true};
const badge=l=>`<span class="lv" style="background:${LV[l][1]}2a;color:${LV[l][1]}">${LV[l][0]} ${l} · ${LV[l][2]}</span>`;
const M=D.meta||{},MT=(M.metrics||{}),TM=MT.timing||{},CB=MT.cib||{},FA=MT.false_alarms||{};
const rowAt=h=>N.r.find(x=>x.h===h)||N.r[N.r.length-1];
const polAt=h=>(N.pol||[]).filter(x=>x.h<=h).slice(-1)[0]||null;
const joinedOf=(a,ex)=>{if(!ex||!ex.size)return N.joined[a];const ab=N.ab[String(a)];if(!ab)return undefined;const e=ab.filter(x=>!ex.has(x[0])).map(x=>x[1]).sort((p,q)=>p-q);return e.length>=2?e[1]:undefined};
const isSusAt=(a,h,ex)=>{const j=joinedOf(a,ex);return j!=null&&j<=h};
const saidAt=h=>new Set(N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[2]));
const preRow=h=>D.pre?(D.pre.series.find(s=>s.h===h)||D.pre.series[0]):null;
const baseStmt=h=>{if(!D.pre)return null;const sa=D.pre.statements.filter(s=>s.h<=h);return sa.length?sa.reduce((a,s)=>(s.level>a.level||(s.level===a.level&&s.h>a.h))?s:a):null};
let STEP=0,H=13,PLAYING=false,SHOWNOTE=false,JUDGED=false,RAF=null,PLAY_T=null,RPTAG="v2",SIG=20;
// ---------------------------------------------------------------- 단계 정의
const W_H=TM.first_watch_h||13,A_H=TM.first_alert_h||41,C_H=TM.first_critical_h||56,MM_H=D.pre?D.pre.summary.first_mismatch_h:47;
const STEPS=[
 {id:"why",short:"목적",title:"무엇을 위해 존재하나",sub:"외국발 서사가 시민의 말이 되는 순간, 국가는 자기 국민과 싸우는 모양이 된다 — 그 전에 잡고, 근거와 함께 권고한다",hour:W_H,dur:5},
 {id:"flow",short:"어떻게 움직이나",title:"데이터가 흐르는 모습 — 원문 → 가명 계정 → 일반 사용자(집계)",sub:"72시간 가상 시나리오를 처음부터 끝까지 재생합니다. 말의 내용이 아니라 누가·언제·무엇을 함께 올렸는지만 봅니다",hour:72,anim:[0,72,10],dur:10},
 {id:"watch",short:`${W_H}시 관찰`,title:`${W_H}시 — 반복 동시 게시가 확인되어 '관찰'`,sub:"신생 계정들이 10분 안에 같은 링크·거의 같은 문장을 두 번 반복 → 내용이 아니라 행동으로 잡힌다",hour:W_H,dur:8},
 {id:"alert",short:`${A_H}시 경보`,title:`${A_H}시 — 일반 사용자 간 확산이 1에 다가가 '경보'`,sub:"점추정이 아니라 확률로 판단한다. 출처 근거가 아직 선명한 마지막 구간에서 공개 대응 수위를 올린다",hour:A_H,anim:[W_H,A_H,3],dur:8},
 {id:"pre",short:"전조 카드",title:`전조 카드 — 공식 발언과 은밀 증폭이 어긋나는 ${MM_H}시`,sub:"공식 신호(A)·명분 서사(B)·은밀 증폭(C)의 정합성. 말이 부드러워질 때 행동이 오르면 '불일치'",hour:MM_H,anim:[A_H,MM_H,1.5],dur:7},
 {id:"fa",short:"오경보·회피",title:"오경보를 내지 않는다 — 그리고 회피는 측정했다",sub:"정상 서사 6개에는 경보 0. 공격자가 시각을 흩뜨리면 어디까지 버티는지 레드팀으로 쟀다",hour:72,dur:5},
 {id:"duel",short:"회피 대결",title:"공격자가 시각을 흩뜨린다 — 창 없는 제3 신호층이 받친다",sub:"버튼으로 공격자의 분산 폭(±σ분)을 올려 보세요. 10분 창 burst 층과 창 없는 감쇠 다층 층의 재현율이 같이 움직입니다 (실험 4 · 시드 3 평균)",hour:72,dur:6},
 {id:"real",short:"실데이터·실제 담화",title:"실데이터와 실제 공개 담화로 확인한 것",sub:"공개 IRA 트윗 약 20만 건 · 실제 공개 담화 10건 — 좋은 결과와 나쁜 결과를 같이 둔다",hour:72,dur:5},
 {id:"human",short:"사람이 결정한다",title:"시스템은 판정하지 않는다 — 판정 · 브리핑 · 지휘관 화면",sub:"판정은 근거를 다시 세고 체인에 기록된다. 단계는 자동으로 내려가지 않는다",hour:A_H,dur:6}];
// ---------------------------------------------------------------- 차트들
function chartFlow(el,h,height){
  const vis=N.posts.filter(p=>p[0]<h),srcs=N.posts.filter(p=>p[3]!=="ko"&&p[0]<h);
  const XY=p=>(p[3]==="ko"&&!isSusAt(p[2],h))?[Math.floor(p[0])+.5,Math.round(p[1])]:[p[0],p[1]];
  const ex=[],ey=[],ux=[],uy=[];
  vis.forEach(p=>{if(p[4]>=0&&N.posts[p[4]][0]<h){const a=XY(N.posts[p[4]]),b=XY(p);ex.push(a[0],b[0],null);ey.push(a[1],b[1],null)}});
  vis.forEach(p=>{if(p[5]&&srcs.length){const q=srcs.reduce((a,s)=>(s[0]<p[0]&&(!a||s[0]>a[0]))?s:a,null)||srcs[0];ux.push(q[0],p[0],null);uy.push(q[1],p[1],null)}});
  const grp=p=>p[3]!=="ko"?"외국어 출처":(isSusAt(p[2],h)?"의심 집단(가명)":"일반 사용자(집계)");
  const tr=[{x:ux,y:uy,mode:"lines",line:{color:CC().src,width:1,dash:"dot"},opacity:.5,hoverinfo:"skip",name:"출처 URL 공유"},{x:ex,y:ey,mode:"lines",line:{color:cssVar("--muted"),width:1},opacity:.55,hoverinfo:"skip",name:"리포스트·답글"}];
  [["외국어 출처",CC().src],["의심 집단(가명)",CC().sus],["일반 사용자(집계)",CC().ord]].forEach(([nm,col])=>{const d=vis.filter(p=>grp(p)===nm);
    if(nm!=="일반 사용자(집계)"){if(d.length)tr.push({x:d.map(p=>p[0]),y:d.map(p=>p[1]),mode:"markers",name:nm,marker:{color:col,size:nm==="외국어 출처"?13:9,line:{color:"#fff",width:1.2}},text:d.map(p=>N.accounts[p[2]]+" · "+p[3]+"<br>"+esc(p[6])),hovertemplate:"%{text}<extra>"+nm+"</extra>"})}
    else{const m={};d.forEach(p=>{const k=(Math.floor(p[0])+.5)+"|"+Math.round(p[1]);m[k]=(m[k]||0)+1});const ks=Object.keys(m);if(ks.length)tr.push({x:ks.map(k=>+k.split("|")[0]),y:ks.map(k=>+k.split("|")[1]),mode:"markers",name:nm,marker:{color:col,size:ks.map(k=>7+3*Math.sqrt(m[k])),opacity:.8,line:{color:"#fff",width:1}},customdata:ks.map(k=>m[k]),hovertemplate:"일반 사용자 %{customdata}건 (집계 · 개별 계정 표시 안 함)<extra></extra>"})}});
  const xmax=Math.max(16,Math.min(D.max_h,Math.ceil(h/8)*8+2));
  Plotly.react(el,tr,{...BASE(),height,margin:{l:48,r:14,t:8,b:44},legend:{orientation:"h",y:-.14,x:0,font:{size:11}},
    shapes:[{type:"line",x0:h,x1:h,yref:"paper",y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}}],
    xaxis:{range:[0,xmax],title:"시작 후 시간",gridcolor:GRID()},yaxis:{title:"출처로부터 단계 (0 = 외국어 원문)",gridcolor:GRID(),dtick:1,rangemode:"tozero"}},cfg)}
function chartVolume(el,h,height){
  const ord=Array(D.max_h+1).fill(0),sus=Array(D.max_h+1).fill(0);
  N.posts.forEach(p=>{if(p[3]!=="ko"||p[0]>=h)return;(isSusAt(p[2],h)?sus:ord)[Math.floor(p[0])]++});
  const xs=[...Array(D.max_h+1).keys()],shapes=N.bursts.filter(b=>b.e<h).map(b=>({type:"rect",xref:"x",yref:"paper",x0:b.s-.45,x1:b.e+.45,y0:0,y1:1,fillcolor:cssVar("--muted"),opacity:.22,line:{width:0}}));
  shapes.push({type:"line",xref:"x",yref:"paper",x0:h,x1:h,y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}});
  const ann=N.bursts.filter(b=>b.e<h).map((b,i)=>({x:(b.s+b.e)/2,y:1,xref:"x",yref:"paper",yanchor:"bottom",text:`burst ${i+1}`,showarrow:false,font:{size:10,color:"#6b6b66"}}));
  Plotly.react(el,[{type:"bar",x:xs,y:ord,name:"일반 사용자",marker:{color:CC().ord}},{type:"bar",x:xs,y:sus,name:"의심 집단",marker:{color:CC().sus}}],
    {...BASE(),height,barmode:"stack",bargap:.2,margin:{l:40,r:12,t:34,b:40},shapes,annotations:ann,legend:{orientation:"h",y:1.12,x:0,font:{size:11}},
     xaxis:{range:[0,Math.max(24,Math.min(D.max_h,h+6))],title:"시작 후 시간",gridcolor:GRID()},yaxis:{gridcolor:GRID(),title:"시간당 게시물"}},cfg)}
function chartR(el,h,height){
  const rs=N.r.filter(x=>x.h<=h),rb=rs.filter(x=>x.lo!=null),mx=Math.max(1.6,...rs.map(x=>x.hi||0))+.1;
  Plotly.react(el,[{x:rb.map(x=>x.h).concat(rb.map(x=>x.h).reverse()),y:rb.map(x=>x.hi).concat(rb.map(x=>x.lo).reverse()),fill:"toself",fillcolor:"rgba(42,120,214,0.15)",line:{width:0},hoverinfo:"skip",name:"80% 구간"},
    {x:rs.map(x=>x.h),y:rs.map(x=>x.r),mode:"lines+markers",line:{color:CC().ord,width:2.5},marker:{size:6},name:"R̂",customdata:rs.map(x=>[x.lo,x.hi,x.p1]),hovertemplate:"%{x}시 · R̂ %{y:.2f} · P(R>1) %{customdata[2]:.0%}<extra></extra>"}],
    {...BASE(),height,showlegend:false,margin:{l:40,r:12,t:26,b:44},
     shapes:[{type:"rect",xref:"paper",x0:0,x1:1,y0:D.r_alert,y1:1,fillcolor:"#ec835a",opacity:.12,line:{width:0}},{type:"line",xref:"paper",x0:0,x1:1,y0:1,y1:1,line:{color:"#d03b3b",width:1.2}},{type:"line",x0:h,x1:h,yref:"paper",y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}}],
     annotations:[{xref:"paper",x:0,y:1,yanchor:"bottom",xanchor:"left",text:"R = 1 자생 확산",showarrow:false,font:{size:11,color:"#d03b3b"}},{xref:"paper",x:0,y:D.r_alert,yanchor:"top",xanchor:"left",text:`경보 기준 R>${D.r_alert} 확률 50%`,showarrow:false,font:{size:10,color:"#b35a2e"}}],
     xaxis:{range:[0,D.max_h],title:"시작 후 시간",gridcolor:GRID()},yaxis:{range:[0,mx],gridcolor:GRID(),title:"일반 사용자 간 R̂"}},cfg)}
function chartPre(el,h,height){
  const P=D.pre,sa=P.statements.filter(s=>s.h<=h),bi=P.items.filter(x=>x.h<=h),cs=P.series.filter(s=>s.h<=h);
  const tr=[{x:[0,P.max_h],y:[0,0],mode:"lines",line:{color:AXC().D,width:1,dash:"dot"},hoverinfo:"skip",showlegend:false},
    {x:cs.map(s=>s.h),y:cs.map(()=>1),mode:"markers",marker:{symbol:"square",size:9,color:cs.map(s=>PLVC[s.c_label])},customdata:cs.map(s=>s.c_label),hovertemplate:"%{x}시 · 축 C %{customdata}<extra></extra>",showlegend:false}];
  const SYM={pretext:"circle",victim:"triangle-up",mobilization:"square",other:"x"};
  if(bi.length)tr.push({x:bi.map(x=>x.h),y:bi.map(()=>2),mode:"markers",marker:{symbol:bi.map(x=>SYM[x.kind]),size:12,color:AXC().B,line:{color:"#fff",width:1}},text:bi.map(x=>`${x.ts} · ${x.lang} · ${esc(x.outlet)}<br>${x.kind_label}`),hovertemplate:"%{text}<extra>B</extra>",showlegend:false});
  const shapes=[];
  if(sa.length){tr.push({x:sa.map(s=>s.h),y:sa.map(()=>3),mode:"markers+text",marker:{symbol:sa.map(s=>s.tone==="soft"?"diamond-open":"diamond"),size:sa.map(s=>9+5*s.level),color:AXC().A,line:{color:AXC().A,width:2}},text:sa.map(s=>`${s.stmt_id} L${s.level}`),textposition:"top center",textfont:{size:10,color:AXC().A},customdata:sa.map(s=>`${s.ts}<br>${s.level_why}`),hovertemplate:"%{customdata}<extra>A</extra>",showlegend:false});
    sa.forEach(s=>{if(s.level>=3&&s.deadline_hours){const [lo,hi]=s.deadline_hours;shapes.push({type:"rect",xref:"x",yref:"y",x0:s.h+lo,x1:Math.min(s.h+hi,P.max_h),y0:2.72,y1:3.28,fillcolor:AXC().A,opacity:.1,line:{color:AXC().A,width:1,dash:"dot"}})}})}
  tr.push({x:cs.map(s=>s.h),y:cs.map(s=>s.conv),mode:"lines",line:{shape:"hv",color:cssVar("--ink"),width:2},fill:"tozeroy",fillcolor:`rgba(${hex2rgb(cssVar("--ink"))},0.08)`,hovertemplate:"%{x}시 · 수렴 %{y}/3축<extra></extra>",showlegend:false,yaxis:"y2"});
  let rs=null,rst=null;[...cs,null].forEach(s=>{const st=s?s.state:null;if(st!==rst){if(["rhetoric_only","converged","mismatch"].includes(rst))shapes.push({type:"rect",xref:"x",yref:"y2",x0:rs-.5,x1:(s?s.h:h+1)-.5,y0:0,y1:3.3,fillcolor:PST[rst][1],opacity:.13,line:{width:0}});rs=s?s.h:null;rst=st}});
  shapes.push({type:"line",xref:"x",yref:"paper",x0:h,x1:h,y0:0,y1:1,line:{dash:"dot",color:"#6b6b66"}});
  Plotly.react(el,tr,{...BASE(),height,margin:{l:98,r:10,t:10,b:36},shapes,
    annotations:[{x:P.max_h/2,y:0,xref:"x",yref:"y",yshift:10,text:"축 D 물리 전조 — 데이터 없음(연결 예정)",showarrow:false,font:{size:10,color:AXC().D}},{xref:"paper",yref:"paper",x:0,y:.29,xanchor:"left",yanchor:"bottom",text:"수렴 축 수 · 띠 = 상태(보라 수사 단독 · 빨강 수렴 · 자주 불일치)",showarrow:false,font:{size:10,color:"#6b6b66"}}],
    xaxis:{range:[0,P.max_h],title:"시작 후 시간",anchor:"y2",gridcolor:GRID()},
    yaxis:{domain:[.36,1],tickvals:[0,1,2,3],ticktext:["D 물리","C 은밀 증폭","B 명분·동원","A 공식 신호"],range:[-.6,3.75],gridcolor:GRID(),zeroline:false,tickfont:{size:11}},
    yaxis2:{domain:[0,.27],range:[0,3.3],tickvals:[0,1,2,3],ticktext:["0","1","2","3"],gridcolor:GRID(),tickfont:{size:10}}},cfg)}
function chartRed(el,height){
  const R=D.red;if(!R){el.innerHTML='<div class="mean" style="padding:20px">레드팀 결과 파일 없음</div>';return}
  const rows=R.rows,xs=rows.map((_,i)=>i),SH={base:"기본<br>(동시 게시)",jitter20:"시각<br>±20분",jitter60:"시각<br>±60분",jitter180:"시각<br>±180분",newsfeed:"뉴스<br>사칭형",newsfeed_mix:"+ 인기 링크<br>희석",newsfeed_uniq:"+ 고유<br>단축 URL"};
  Plotly.react(el,[{x:xs,y:rows.map(x=>x[2]),mode:"lines+markers",name:"burst 층(동시 게시)",line:{color:R.colors.burst,width:3},marker:{size:8}},
    {x:xs,y:rows.map(x=>x[3]),mode:"lines+markers",name:"URL-망 층(함께 미는 링크)",line:{color:R.colors.url,width:3},marker:{size:8}}],
    {...BASE(),height,margin:{l:40,r:10,t:8,b:62},legend:{orientation:"h",y:1.12,x:0,font:{size:11}},
     xaxis:{tickvals:xs,ticktext:rows.map(x=>SH[x[0]]||x[1]),tickfont:{size:10},tickangle:0,range:[-.5,rows.length-.5]},yaxis:{range:[-.05,1.08],title:"공작 계정 재현율",gridcolor:GRID()}},cfg)}
function chartDuel(el,height){
  const U=D.duel,xs=U.rows.map((_,i)=>i);
  Plotly.react(el,[{x:xs,y:U.rows.map(r=>r.burst),mode:"lines+markers",name:"burst 층(10분 창)",line:{color:U.colors.burst,width:3},marker:{size:8}},
    {x:xs,y:U.rows.map(r=>r.decay),mode:"lines+markers",name:"제3 신호층(창 없음)",line:{color:U.colors.decay,width:3},marker:{size:8}},
    {x:[U.rows.findIndex(r=>r.sigma===SIG)],y:[0],mode:"markers",name:"지금 보는 σ",marker:{size:14,symbol:"triangle-up",color:"#f0b429"},showlegend:false}],
    {...BASE(),height,margin:{l:40,r:10,t:8,b:40},legend:{orientation:"h",y:1.12,x:0,font:{size:11}},
     xaxis:{tickvals:xs,ticktext:U.rows.map(r=>"±"+r.sigma),title:"공격자의 시각 분산 폭 (분)",tickfont:{size:10},range:[-.5,U.rows.length-.5]},yaxis:{range:[-.05,1.08],title:"공작 계정 재현율",gridcolor:GRID()}},cfg)}
function chartIRA(el,height){
  const R=D.real;const name={HashtagGamer:"해시태그 게임",LeftTroll:"좌파 사칭",RightTroll:"우파 사칭",NonEnglish:"비영어(러시아어 등)",NewsFeed:"뉴스 매체 사칭"};
  const items=Object.entries(R.repeated_by_category).filter(([k])=>(R.accounts_by_category[k]||0)>=5).sort((a,b)=>a[1]-b[1]);
  Plotly.react(el,[{type:"bar",orientation:"h",y:items.map(([k])=>`${name[k]||k} (${R.accounts_by_category[k]})`),x:items.map(([,v])=>v),marker:{color:items.map(([k])=>k==="NewsFeed"?"#b5b4ad":CC().sus)},text:items.map(([,v])=>Math.round(v*100)+"%"),textposition:"outside",hoverinfo:"skip"}],
    {...BASE(),height,margin:{l:150,r:46,t:8,b:30},xaxis:{range:[0,1.32],tickformat:".0%",gridcolor:GRID(),tickvals:[0,.5,1]},yaxis:{automargin:true,tickfont:{size:11.5}}},cfg)}
function chartReplay(el,height,tag){
  const R=D.replay;if(!R){el.innerHTML="";return}const RLV={0:"#d9d8d2",1:"#b5b4ad",2:"#e0a000",3:"#d03b3b"};
  const cases=R.cases.filter(c=>c.verdict[tag].result!=="n/a"),tr=[],shapes=[],ann=[];
  cases.forEach((c,i)=>{const y=cases.length-1-i;if(c.kind==="precedent"&&c.action_date)shapes.push({type:"line",x0:0,x1:0,y0:y-.42,y1:y+.42,line:{color:cssVar("--ink"),width:3}});
    else{shapes.push({type:"rect",x0:0,x1:c.window_days,y0:y-.3,y1:y+.3,fillcolor:"#9a9a94",opacity:.12,line:{width:0}})}
    c.statements.filter(s=>!s.excluded).forEach(s=>{const lv=s[tag].level;tr.push({x:[s.rel_days],y:[y],mode:"markers",showlegend:false,marker:{symbol:"diamond",size:8+4*lv,color:RLV[lv],line:{color:"#fff",width:1}},hovertemplate:`${s.date} · ${esc(s.speaker_role)}<br>${tag} L${lv} (${s[tag].level_why})<br>${esc(s.text_ko.slice(0,80))}…<extra></extra>`})})});
  const PE=(D.sat&&D.sat.physical_events)||[];
  cases.forEach((c,i)=>{const y=cases.length-1-i;const ev=PE.filter(e=>e.case_id===c.case_id&&e.date&&c.action_date&&c.kind==="precedent").map(e=>({...e,rd:Math.round((new Date(e.date)-new Date(c.action_date))/864e5)}));if(!ev.length)return;
    const inR=ev.filter(e=>e.rd>=-8.5&&e.rd<=15),left=ev.filter(e=>e.rd<-8.5),right=ev.filter(e=>e.rd>15),MK="#9a9a94";
    if(inR.length)tr.push({x:inR.map(e=>e.rd),y:inR.map(()=>y-.33),mode:"markers",showlegend:false,marker:{symbol:"triangle-down",size:10,color:MK,line:{color:"#fff",width:1}},text:inR.map(e=>`${e.date} · ${esc(e.what)}`),hovertemplate:"%{text}<extra>물리 신호</extra>"});
    if(left.length){const lo=Math.min(...left.map(e=>e.rd)),hi=Math.max(...left.map(e=>e.rd));tr.push({x:[-8.2],y:[y-.33],mode:"markers+text",showlegend:false,marker:{symbol:"triangle-down",size:10,color:MK,line:{color:"#fff",width:1}},text:[`◀${left.length}건 ${lo}~${hi}일`],textposition:"bottom right",textfont:{size:9,color:MK},hovertemplate:left.map(e=>`${e.date} (${e.rd}일) · ${esc(e.what.slice(0,60))}`).join("<br>")+"<extra>물리 신호</extra>"})}
    if(right.length){tr.push({x:[14.6],y:[y-.33],mode:"markers+text",showlegend:false,marker:{symbol:"triangle-down",size:10,color:MK,line:{color:"#fff",width:1}},text:[`▶${right.length}건`],textposition:"bottom left",textfont:{size:9,color:MK},hovertemplate:right.map(e=>`${e.date} (+${e.rd}일) · ${esc(e.what.slice(0,60))}`).join("<br>")+"<extra>물리 신호</extra>"})}});
  ann.push({xref:"paper",yref:"paper",x:0,y:1.02,xanchor:"left",yanchor:"bottom",text:"◆ L3 빨강 · L2 노랑 · L1 회색 · 검은 선 = 행동일 · 띠 = 14일 내 행동 없음"+(PE.length?" · ▽ 물리 신호":""),showarrow:false,font:{size:9.5,color:"#6b6b66"}});
  Plotly.react(el,tr,{...BASE(),height,margin:{l:10,r:10,t:22,b:40},shapes,annotations:ann,xaxis:{title:{text:"상대 일수 (행동일 = 0 · 행동 없는 사례는 첫 발언 = 0)",font:{size:10.5}},range:[-8.5,15],zeroline:false,gridcolor:GRID(),dtick:4,tickangle:0,tickfont:{size:10}},
    yaxis:{automargin:true,tickvals:cases.map((_,i)=>i),ticktext:[...cases].reverse().map(c=>`${c.case_id.slice(0,2)} ${c.name.split("(")[0].slice(0,10)}…`),tickfont:{size:10},range:[-.6,cases.length-.4]}},cfg)}
// ---------------------------------------------------------------- 그래프 뷰 (Obsidian 그래프 스타일 · obsgraph_template.html 이식)
let GRAPH=null,FLOWVIEW="graph";
const hex2rgb=h=>{h=h.replace("#","");if(h.length===3)h=h.split("").map(c=>c+c).join("");const n=parseInt(h,16);return `${(n>>16)&255},${(n>>8)&255},${n&255}`};
function makeGraph(cv,G,onTick){
  const ctx=cv.getContext("2d");
  const N=G.nodes.map((n,i)=>Object.assign({},n,{i,x:0,y:0,vx:0,vy:0,born:false,deg:0,nb:[]}));
  const E=G.edges.map(e=>({a:e[0],b:e[1],t:e[2],k:e[3],from:e[4],c:false})),Cc=G.coord.map(e=>({a:e[0],b:e[1],t:e[2],w:e[3],c:true}));
  const ALL=E.concat(Cc);ALL.forEach(e=>{N[e.a].nb.push(e);N[e.b].nb.push(e)});const PO=G.posts;
  let T=0,alpha=1,W=0,Hh=0,DPR=1,view={x:0,y:0,k:1},hover=null,pulses=[],follow=true,dragNode=null,pan=null,raf=null,dead=false,lastTick=0;
  const col=()=>({ord:cssVar("--g-ord"),sus:cssVar("--g-sus"),src:cssVar("--g-src")});
  function resize(){DPR=window.devicePixelRatio||1;W=cv.clientWidth;Hh=cv.clientHeight;cv.width=W*DPR;cv.height=Hh*DPR}
  const kind=(n,t)=>n.fo?"src":((n.tj!=null&&n.tj<=t)?"sus":"ord"),vis=(n,t)=>n.tf<=t,evis=(e,t)=>e.t<=t&&N[e.a].tf<=t&&N[e.b].tf<=t;
  function birth(n){let anchor=null;for(const e of n.nb){const o=N[e.a===n.i?e.b:e.a];if(o.born&&o.tf<=n.tf){anchor=o;break}}
    const r=anchor?18+Math.random()*16:60+Math.random()*80,a=Math.random()*6.283,bx=anchor?anchor.x:0,by=anchor?anchor.y:0;n.x=bx+Math.cos(a)*r;n.y=by+Math.sin(a)*r;n.vx=n.vy=0;n.born=true;alpha=Math.min(1,alpha+0.03)}
  function tick(){const vs=N.filter(n=>vis(n,T));vs.forEach(n=>{if(!n.born)birth(n);n.deg=0});const CELL=110,grid=new Map();
    for(const n of vs){const k=((n.x/CELL)|0)+","+((n.y/CELL)|0);(grid.get(k)||grid.set(k,[]).get(k)).push(n)}
    for(const n of vs){const gx=(n.x/CELL)|0,gy=(n.y/CELL)|0;for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){const cell=grid.get((gx+dx)+","+(gy+dy));if(!cell)continue;
      for(const m of cell){if(m.i<=n.i)continue;let x=n.x-m.x,y=n.y-m.y,d2=x*x+y*y+0.01;if(d2>CELL*CELL)continue;const f=420*alpha/d2;n.vx+=x*f;n.vy+=y*f;m.vx-=x*f;m.vy-=y*f}}}
    for(const e of ALL){if(!evis(e,T))continue;const a=N[e.a],b=N[e.b];a.deg++;b.deg++;const L=e.c?26:38,s=e.c?0.06:0.035;let x=b.x-a.x,y=b.y-a.y,d=Math.sqrt(x*x+y*y)||1;const f=(d-L)/d*s*alpha;a.vx+=x*f;a.vy+=y*f;b.vx-=x*f;b.vy-=y*f}
    for(const n of vs){n.vx-=n.x*0.0018*alpha;n.vy-=n.y*0.0018*alpha;n.vx*=0.82;n.vy*=0.82;if(n!==dragNode){n.x+=n.vx;n.y+=n.vy}}alpha=Math.max(0.12,alpha*0.995)}
  const rad=n=>Math.max((n.fo?7:2.6)+1.25*Math.sqrt(n.deg),(n.fo?4.5:1.7)/view.k);
  function draw(now){const C=col(),bg=cssVar("--bg");ctx.setTransform(DPR,0,0,DPR,0,0);ctx.fillStyle=bg;ctx.fillRect(0,0,W,Hh);ctx.setTransform(DPR*view.k,0,0,DPR*view.k,DPR*view.x,DPR*view.y);
    const hl=hover?new Set([hover.i,...hover.nb.filter(e=>evis(e,T)).map(e=>e.a===hover.i?e.b:e.a)]):null,EDGE=cssVar("--g-edge");
    for(const e of ALL){if(!evis(e,T))continue;const a=N[e.a],b=N[e.b],age=T-e.t,on=!hl||(hl.has(e.a)&&hl.has(e.b)&&(e.a===hover.i||e.b===hover.i));let c,w=1/view.k*(e.c?1.3:0.8),al;
      if(e.c){c=hex2rgb(C.sus);al=0.42}else if(e.k==="u"){c=hex2rgb(C.src);al=0.30}else{c=EDGE;al=0.13}
      if(age<1.5&&!e.c)al=Math.max(al,0.75*(1-age/1.5));if(!on)al*=0.12;else if(hl)al=Math.min(1,al*3.2);
      ctx.strokeStyle=`rgba(${c},${al})`;ctx.lineWidth=w;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
    pulses=pulses.filter(p=>now-p.s<900);
    for(const p of pulses){const n=N[p.n];if(!vis(n,T))continue;const q=(now-p.s)/900;ctx.strokeStyle=p.big?`rgba(${hex2rgb(C.sus)},${0.9*(1-q)})`:`rgba(${p.c},${0.55*(1-q)})`;ctx.lineWidth=(p.big?2.2:1.1)/view.k;ctx.beginPath();ctx.arc(n.x,n.y,rad(n)+(p.big?34:12)*q,0,6.283);ctx.stroke()}
    for(const pass of ["ord","src","sus"]){for(const n of N){if(!vis(n,T))continue;const kd=kind(n,T);if(kd!==pass)continue;const dim=hl&&!hl.has(n.i),r=rad(n);ctx.globalAlpha=dim?0.13:1;
      if(kd!=="ord"&&!dim){ctx.shadowColor=C[kd];ctx.shadowBlur=14*view.k}ctx.fillStyle=(hover===n)?cssVar("--acc"):C[kd];ctx.beginPath();ctx.arc(n.x,n.y,r,0,6.283);ctx.fill();ctx.shadowBlur=0;
      const fresh=T-n.tf<0.6;if(fresh&&!dim){ctx.strokeStyle="rgba(255,255,255,.7)";ctx.lineWidth=1/view.k;ctx.stroke()}}}
    ctx.globalAlpha=1;ctx.font=`${11/view.k}px -apple-system,"Apple SD Gothic Neo",sans-serif`;ctx.textAlign="center";
    for(const n of N){if(!vis(n,T))continue;const kd=kind(n,T);if(kd==="ord"||!n.id)continue;if(!((n.fo&&view.k>0.45)||view.k>1.25||(hl&&hl.has(n.i))))continue;if(hl&&!hl.has(n.i))continue;
      ctx.fillStyle=kd==="src"?`rgba(${hex2rgb(C.src)},.95)`:`rgba(${hex2rgb(C.sus)},.9)`;ctx.fillText(n.fo?"외국어 출처 · "+n.id:n.id,n.x,n.y-rad(n)-5/view.k)}}
  function target(){const vs=N.filter(n=>vis(n,T)&&n.born);if(!vs.length)return null;let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;vs.forEach(n=>{x0=Math.min(x0,n.x);x1=Math.max(x1,n.x);y0=Math.min(y0,n.y);y1=Math.max(y1,n.y)});
    const k=Math.min(3.2,Math.min((W-40)/(x1-x0+90),(Hh-110)/(y1-y0+90)));return {k,x:W/2-k*(x0+x1)/2,y:(Hh+22)/2-k*(y0+y1)/2}}
  let idleT=null;const pauseFollow=()=>{follow=false;clearTimeout(idleT);idleT=setTimeout(()=>{follow=true},4000)};   // 손을 떼면 4초 뒤 다시 자동 화면 맞춤
  function followCam(){if(!follow)return;const g=target();if(!g)return;const a=0.08;view.k+=(g.k-view.k)*a;view.x+=(g.x-view.x)*a;view.y+=(g.y-view.y)*a}
  function counts(){let c={src:0,sus:0,ord:0},np=0;for(const n of N)if(vis(n,T))c[kind(n,T)]++;for(const p of PO){if(p[0]>T)break;np++}return {...c,np,ce:Cc.filter(e=>evis(e,T)).length}}
  function emit(a,b){const now=performance.now();let cnt=0;for(const p of PO){if(p[0]<=a)continue;if(p[0]>b)break;if(++cnt>60)break;const n=N[p[1]];pulses.push({n:p[1],s:now,c:n.fo?hex2rgb(col().src):cssVar("--g-edge")})}
    for(const n of N){if(n.tj!=null&&n.tj>a&&n.tj<=b)pulses.push({n:n.i,s:now,big:true})}}
  function seek(t){const nt=Math.max(0,Math.min(G.max_h,t));if(nt>T&&nt-T<3)emit(T,nt);T=nt;alpha=Math.min(1,alpha+0.3)}
  function loop(now){if(dead)return;tick();followCam();draw(now);if(now-lastTick>250){lastTick=now;onTick&&onTick(counts(),T)}raf=requestAnimationFrame(loop)}
  const toW=(sx,sy)=>[(sx-view.x)/view.k,(sy-view.y)/view.k];
  function pick(sx,sy){const [x,y]=toW(sx,sy);let best=null,bd=1e9;for(const n of N){if(!vis(n,T))continue;const d=(n.x-x)**2+(n.y-y)**2,r=rad(n)+5/view.k;if(d<r*r&&d<bd){bd=d;best=n}}return best}
  const tip=cv.parentElement.querySelector(".gtip");
  const onDown=e=>{const n=pick(e.offsetX,e.offsetY);if(n)dragNode=n;else{pan=[e.offsetX-view.x,e.offsetY-view.y];pauseFollow()}cv.style.cursor="grabbing"};
  const onUp=()=>{dragNode=null;pan=null;cv.style.cursor="grab"};
  const onMove=e=>{if(dragNode){const [x,y]=toW(e.offsetX,e.offsetY);dragNode.x=x;dragNode.y=y;alpha=Math.max(alpha,0.4);return}if(pan){view.x=e.offsetX-pan[0];view.y=e.offsetY-pan[1];return}
    hover=pick(e.offsetX,e.offsetY);if(!tip)return;if(!hover){tip.style.display="none";return}const kd=kind(hover,T),np=PO.filter(p=>p[1]===hover.i&&p[0]<=T).length,deg=hover.nb.filter(x=>evis(x,T)).length,C=col();
    let h=kd==="src"?`<b style="color:${C.src}">외국어 출처</b> · ${hover.id}`:kd==="sus"?`<b style="color:${C.sus}">행동 기준 의심</b>${hover.id?" · "+hover.id:""}`:`<b style="color:${C.ord}">일반 사용자</b> <span class="muted">(이름표 없음)</span>`;
    h+=`<br>처음 등장 ${fmt(hover.tf)} · 게시 ${np}건 · 연결 ${deg}개`;if(kd==="sus"&&hover.tj!=null)h+=`<br>반복 동시 게시로 의심 확정 ${fmt(hover.tj)}`;
    tip.innerHTML=h;tip.style.display="block";tip.style.left=Math.min(W-270,e.offsetX+14)+"px";tip.style.top=(e.offsetY+14)+"px"};
  const onLeave=()=>{hover=null;if(tip)tip.style.display="none"};
  const onWheel=e=>{e.preventDefault();pauseFollow();const f=Math.exp(-e.deltaY*0.0015),k=Math.max(0.25,Math.min(5,view.k*f));view.x=e.offsetX-(e.offsetX-view.x)*k/view.k;view.y=e.offsetY-(e.offsetY-view.y)*k/view.k;view.k=k};
  cv.addEventListener("mousedown",onDown);window.addEventListener("mouseup",onUp);cv.addEventListener("mousemove",onMove);cv.addEventListener("mouseleave",onLeave);cv.addEventListener("wheel",onWheel,{passive:false});
  const onResize=()=>{resize();fit()};window.addEventListener("resize",onResize);resize();view.x=W/2;view.y=Hh/2;
  function fit(){const g=target();if(g){view.k=g.k;view.x=g.x;view.y=g.y}follow=true}
  function destroy(){dead=true;if(raf)cancelAnimationFrame(raf);window.removeEventListener("mouseup",onUp);window.removeEventListener("resize",onResize)}
  return {seek,fit,destroy,counts,warm(t){seek(t);for(let i=0;i<(t>0?260:40);i++)tick();fit()},start(){raf=requestAnimationFrame(loop)},get T(){return T}}}
function flowHud(c,t){const el=document.getElementById("ghud");if(!el||!c)return;const C=col3();
  const lv=rowAt(Math.max(1,Math.floor(t))).level;
  el.innerHTML=`<div style="font-size:20px;font-weight:700;letter-spacing:-.3px">${Math.floor(t)}시 <span class="muted" style="font-size:11.5px;font-weight:400">${fmt(Math.floor(t))}</span> <span class="lv" style="font-size:11px;padding:2px 8px;background:${LV[lv][1]}2a;color:${LV[lv][1]}">${LV[lv][0]} ${LV[lv][2]}</span></div><span class="dot" style="background:${C.src}"></span>외국어 출처 <b>${c.src}</b><br><span class="dot" style="background:${C.sus}"></span>행동 기준 의심(가명) <b>${c.sus}</b><br><span class="dot" style="background:${C.ord}"></span>일반 사용자 <b>${c.ord}</b><br><span class="muted">게시물 ${c.np}건 · 조정 연결 ${c.ce}개</span>`}
const col3=()=>({ord:cssVar("--g-ord"),sus:cssVar("--g-sus"),src:cssVar("--g-src")});
function killGraph(){if(GRAPH){GRAPH.destroy();GRAPH=null}}
// ---------------------------------------------------------------- 무대 오른쪽 열 (시각이 바뀔 때 이 부분만 갈아 끼운다 → 끊김 없음)
function watchSide(h){
  const said=saidAt(h),nBeh=[...said].filter(a=>isSusAt(a,h)).length,curK=Object.keys(N.scores).filter(a=>isSusAt(+a,h)),cur=curK.map(a=>N.scores[a]),mean=i=>cur.length?cur.reduce((s,v)=>s+v[i],0)/cur.length:0;
  const bSoFar=curK.length?curK.reduce((s,a)=>s+((N.ab[a]||[]).filter(x=>x[1]<=h).length),0)/curK.length:0;
  const pr=polAt(h),lv=rowAt(h).level,fo=N.foreign.filter(f=>f.x<h),koX=N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[0]),firstKo=koX.length?Math.min(...koX):null;
  const lead=fo.length&&firstKo!=null?Math.max(...fo.map(f=>firstKo-f.x)):null;
  const bar=(l,v,txt,col)=>`<div style="display:flex;justify-content:space-between;font-size:12.5px"><span>${l}</span><b>${txt}</b></div><div class="bar"><i style="width:${Math.round(Math.min(1,v)*100)}%;background:${col}"></i></div>`;
  return `<div style="display:flex;justify-content:space-between;align-items:center"><div>${badge(lv)}</div><div style="font-size:12px;color:var(--muted)">외국어 원문 ${fo.length}건${lead!=null?` · 한국어보다 <b>${lead.toFixed(1)}시간</b> 앞섬`:""}</div></div>
      <div style="margin-top:12px;font-size:12px;color:var(--muted)">의심 집단의 행동 신호 (평균)</div>
      ${bar("신생 계정 비율",mean(1),mean(1).toFixed(2),CC().sus)}${bar("동시 게시 반복 (지금까지)",Math.min(bSoFar/4,1),bSoFar.toFixed(1)+"회",CC().sus)}${bar("같은 링크 공유",mean(2),mean(2).toFixed(2),CC().sus)}
      <div class="cmp"><div><div style="font-size:11.5px;color:var(--muted)">내용 기준이면</div><div class="big" style="color:var(--muted)">${said.size}</div><div style="font-size:11.5px;color:var(--muted)">이 서사를 말한 계정 전부</div></div><div class="vs">vs</div><div><div style="font-size:11.5px;color:var(--muted)">행동 기준(우리 방식)</div><div class="big" style="color:${CC().sus}">${nBeh}</div><div style="font-size:11.5px;color:var(--muted)">반복 동시 게시 계정만</div></div></div>
      ${pr?`<div class="pol"><div style="font-size:11.5px;color:var(--muted)">대응 단계 권고</div><b>${esc(pr.al)}</b><div style="font-size:12.5px;margin-top:3px">${esc(pr.lvl)}</div>${pr.dn.length?`<div style="font-size:12px;color:var(--muted);margin-top:4px">하지 말 것 — ${pr.dn.map(esc).join(" · ")}</div>`:""}</div>`:""}`}
function alertSide(h){const rr=rowAt(h),pr=polAt(h),lv=rr.level;
  return `<div>${badge(lv)}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
       <div class="kp"><div class="l">P(R &gt; 0.8)</div><div class="v">${rr.p08==null?"—":Math.round(rr.p08*100)+"%"}</div><div class="n">경보 기준: 50% 이상</div></div>
       <div class="kp"><div class="l">P(R &gt; 1) 자생 확산</div><div class="v">${rr.p1==null?"—":Math.round(rr.p1*100)+"%"}</div><div class="n">R̂ ${rr.r==null?"—":rr.r.toFixed(2)} (${rr.lo==null?"—":rr.lo.toFixed(2)}~${rr.hi==null?"—":rr.hi.toFixed(2)})</div></div>
      </div>
      <div class="kp" style="margin-top:10px"><div class="l">이 시각까지 본 게시물</div><div class="v">${rr.n_sofar}<small>/ ${(TM.ko_posts_total||1501).toLocaleString()}건 (${Math.round(100*rr.n_sofar/(TM.ko_posts_total||1501))}%)</small></div><div class="n">전체의 1/10 시점에 공개 대응 수위를 올린다</div></div>
      ${pr?`<div class="pol"><div style="font-size:11.5px;color:var(--muted)">대응 단계 권고</div><b>${esc(pr.al)}</b><div style="font-size:12.5px;margin-top:3px">${esc(pr.lvl)}</div><div style="font-size:12px;color:var(--muted);margin-top:4px">다음 재평가 — ${esc(pr.esc)}</div></div>`:""}
      <div style="margin-top:10px;font-size:12.5px">${D.seal.ok?"✅":"❌"} 증거 봉인 ${esc(D.seal.msg)} — 관찰 단계부터 출처·시간 순서·게시물 해시를 체인으로 기록</div>`}
let PREMODE="card",SATI=0,SATPOS=50;
function satView(){const S=D.sat;if(!S||!S.sites.length)return '<div class="mean">위성 사례 자료 없음</div>';SATI=Math.min(SATI,S.sites.length-1);const site=S.sites[SATI];
  const tabs=`<div class="sattabs">${S.sites.map((x,i)=>`<button class="btn ${i===SATI?"pri":""}" onclick="SATI=${i};SATPOS=50;renderStage()">${esc(x.title.split(" (")[0])}</button>`).join("")}</div>`;
  const has=site.before.src&&site.after.src;
  const img=has?`<div class="cmpw" id="cmpw"><img src="${site.before.src}" alt="전"><img class="after" id="cmpafter" src="${site.after.src}" alt="후" style="clip-path:inset(0 0 0 ${SATPOS}%)"><div class="div" id="cmpdiv" style="left:${SATPOS}%"></div><span class="lab l">전 · ${esc(site.before.date)}</span><span class="lab r">후 · ${esc(site.after.date)}</span><input type="range" min="0" max="100" value="${SATPOS}" oninput="SATPOS=+this.value;document.getElementById('cmpafter').style.clipPath='inset(0 0 0 '+SATPOS+'%)';document.getElementById('cmpdiv').style.left=SATPOS+'%'"></div>`
    :`<div class="cmpw"><div class="ph"><div>아직 영상 파일이 없습니다 — 아래 두 파일을 <b>백신/4_근거자료/위성/</b>에 넣고 다시 내보내면 전·후 비교로 뜹니다.<code>${esc(site.before.file)} (전 · ${esc(site.before.date)})</code><code>${esc(site.after.file)} (후 · ${esc(site.after.date)})</code></div></div></div>`;
  const coord=site.lat!=null?`${(+site.lat).toFixed(3)}°N ${(+site.lon).toFixed(3)}°E`:"좌표 [확인 필요]";
  return `<div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:15px;font-weight:700">축 D 물리 전조 — 실제 사례 (공개 위성영상)</div><button class="btn" style="padding:3px 8px;font-size:11px" onclick="PREMODE='card';renderStage()">← 정합성 카드</button></div>${tabs}${img}
   <div style="font-size:12.5px;margin-top:8px"><b>${esc(site.title)}</b> · ${esc(site.place)} · ${coord}${site.browser_url?` · <a href="${site.browser_url}" target="_blank" style="color:var(--acc)">Copernicus Browser에서 열기</a>`:""}</div>
   <div style="font-size:12px;color:var(--muted);margin-top:4px"><b>무엇을 보나</b> ${esc(site.what)}<br><b>의미</b> ${esc(site.role)}</div>
   <div class="lim" style="margin-top:8px">${esc(S.disclaimer)} ${esc(S.license_note)}</div>
   <div style="font-size:11px;color:var(--muted);margin-top:6px">${esc(S.attribution)}</div>`}
function preSide(h){if(PREMODE==="sat")return satView();const row=preRow(h),bs=baseStmt(h),sa=D.pre.statements.filter(s=>s.h<=h),L=sa[sa.length-1];
  let quote="";if(bs){const t=bs.text;let out="",last=0;[...bs.spans].sort((a,b)=>a[0]-b[0]).forEach(([a,b,k])=>{if(a<last)return;out+=esc(t.slice(last,a));const f=PF[k]||["",""];out+=`<span title="${f[0]}" style="border-bottom:2px solid ${f[1]};background:${f[1]}14">${esc(t.slice(a,b))}</span>`;last=b});out+=esc(t.slice(last));quote=out}
  const prec=bs?bs.similar.filter(c=>c.kind==="precedent"&&c.match>=2&&(c.axes||["A"]).includes("A")):[];
  const hasSat=D.sat&&D.sat.sites&&D.sat.sites.length;
  const chips=[["A 공식 신호",row.a_level>=2,AXC().A,`L${row.a_level}${row.a_tone==="soft"?" · 최신 톤 완화":""}`,""],["B 명분·동원",row.b_level>=2,AXC().B,row.b_level>=2?`다국어 ${row.b_items}건`:`${row.b_items}건`,""],["C 은밀 증폭",row.c_level>=2,AXC().C,row.c_label,""],["D 물리 전조",false,AXC().D,hasSat?"시나리오 데이터 없음 · 실제 사례 보기 ▸":"데이터 없음",hasSat?"PREMODE='sat';renderStage()":""]];
  return `<div style="display:flex;align-items:baseline;gap:10px"><span style="font-size:26px;font-weight:700;color:${PST[row.state][1]}">${PST[row.state][0]} ${row.state_label}</span><span style="font-size:12px;color:var(--muted)">수렴 ${row.conv}/3축 · ${h}시</span></div>
      <div class="chips" style="margin:8px 0 10px">${chips.map(([n,on,c,t,oc])=>`<span class="chip" style="border-color:${on?c:"var(--line)"};background:${on?c+"22":"var(--panel2)"};${oc?"cursor:pointer;border-style:dashed":""}" ${oc?`onclick="${oc}"`:""}><b style="color:${c}">${n}</b> ${esc(t)}</span>`).join("")}</div>
      ${bs?`<div style="font-size:12px;color:var(--muted)">기준 공식 발언 ${bs.stmt_id} · ${bs.ts} · L${bs.level} (${esc(bs.level_why)}) · 밑줄 = 추출 근거 구절 · 가상 번역문</div><div class="quote">“${quote}”</div>`:'<div class="mean">아직 공식 발언 없음</div>'}
      ${L&&bs&&L!==bs?`<div style="font-size:12.5px;padding:7px 10px;border-left:3px solid var(--ord);background:var(--soft-bg);border-radius:0 8px 8px 0"><b>최신 ${L.stmt_id}</b> · 톤 ${L.tone==="soft"?"완화":"위협"} — “${esc(L.text.slice(0,60))}…”<br><span style="color:var(--muted)">예고는 철회되지 않았다. 완화 발언을 근거로 경계를 낮추지 않는다.</span></div>`:""}
      ${prec.length?`<div style="margin-top:10px;font-size:12.5px"><b>유사 과거 사례 선행</b> (공개 보도 기준 · 참고용) — ${prec.map(c=>`${esc(c.name.split(" (")[0])} <b>${c.lead_days}일</b>`).join(" · ")}</div>`:""}`}
let LASTH=null;
// 시각만 바뀔 때: 무대를 다시 만들지 않고 차트(Plotly.react, 소수 시각)와 오른쪽 열만 갱신 → 영상처럼 이어진다
function updateHour(hf){
  const S=STEPS[STEP],h=Math.floor(hf+1e-6),v1=document.getElementById("v1"),side=document.getElementById("rside"),HH=stageH();
  const clock=document.getElementById("sclock");
  if(S.id==="alert"&&v1){chartR("v1",hf,HH-34);if(h!==LASTH&&side)side.innerHTML=alertSide(h)}
  else if(S.id==="pre"&&v1&&D.pre){chartPre("v1",hf,HH-10);if(h!==LASTH&&side&&PREMODE==="card")side.innerHTML=preSide(h)}
  else if(S.id==="watch"&&v1){chartVolume("v1",hf,HH-34);if(h!==LASTH&&side)side.innerHTML=watchSide(h)}
  else if(S.id==="flow"&&FLOWVIEW==="time"&&v1){chartFlow("v1",hf,HH)}
  else if(h!==LASTH){renderStage()}
  if(["flow","watch","alert","pre","human"].includes(S.id)&&clock)clock.innerHTML=`관측 시각 (시작 후 ${h}시)<b>${fmt(h)}</b>`;
  LASTH=h}
// ---------------------------------------------------------------- 무대(가운데) 렌더
function stageH(){return Math.max(260,document.getElementById("sbody").clientHeight-28)}
function renderStage(){
  const S=STEPS[STEP],h=H,B=document.getElementById("sbody");const HH=stageH();
  document.getElementById("stitle").textContent=S.title;document.getElementById("ssub").textContent=S.sub;LASTH=Math.floor(h);
  if(S.id!=="flow")killGraph();
  const showClock=["flow","watch","alert","pre","human"].includes(S.id);
  document.getElementById("sclock").innerHTML=showClock?`관측 시각 (시작 후 ${h}시)<b>${fmt(h)}</b>`:`<span style="font-size:11.5px">시나리오 72시간 전체 · 자체 측정</span>`;
  if(S.id==="why"){
    const n0=M.narr?M.narr[CAMP]:{},nn=M.narr?Object.keys(M.narr).length:"—";
    B.innerHTML=`<div class="fade" style="height:100%;display:flex;flex-direction:column;justify-content:space-between">
     <div class="pipe">
      <div class="pb"><div class="k">1 입력</div><div class="t">공개 데이터</div><div class="d">SNS·뉴스·커뮤니티 게시물 (시연은 합성 72시간)</div><div class="v">${(M.n_posts||0).toLocaleString()}<small> 게시물 · 계정 ${(M.n_accounts||0).toLocaleString()}</small></div></div>
      <div class="pb"><div class="k">2 서사</div><div class="t">다국어 서사 묶기</div><div class="d">중·러·일·영 원문과 한국어 글을 같은 이야기로 연결</div><div class="v">${nn}<small> 서사 · 외국어 원문 ${M.n_foreign||0}건</small></div></div>
      <div class="pb"><div class="k">3 행동</div><div class="t">조정 행동 신호</div><div class="d">10분 동시 게시 반복 · 같은 링크 · 문장 재사용 · 신생 계정 (+ URL 공유 네트워크)</div><div class="v">${M.n_bursts||0}회<small> burst · 의심 계정 ${M.n_suspected||0}</small></div></div>
      <div class="pb"><div class="k">4 확산</div><div class="t">일반 사용자 간 R̂</div><div class="d">최근 3시간 사후분포로 "자생 확산" 확률을 센다</div><div class="v" style="font-size:18px">${W_H} → ${A_H} → ${C_H}시<small> 관찰·경보·위험</small></div></div>
      <div class="pb"><div class="k">5 권고</div><div class="t">근거 카드 + 대응 수위</div><div class="d">왜 지금·왜 이 수준·하지 말 것·다음 재평가·신뢰도 (+ 전조 카드)</div><div class="v" style="font-size:14.5px">${esc((n0&&n0.pol_first)||"사전 반박 준비")}<small> → ${A_H}시 실행 검토</small></div></div>
      <div class="pb"><div class="k">6 사람</div><div class="t">봉인 · 판정 · 브리핑</div><div class="d">단계마다 증거 해시 봉인, 분석관 판정 기록, 1쪽 브리핑, 지휘관 화면</div><div class="v">${M.n_chain||0}건<small> 봉인 · 최종 결정은 사람</small></div></div>
     </div>
     <div class="prin">
      <div class="pr"><b>내용이 아니라 행동</b><span>같은 주장을 하는 시민은 공작이 아니다. 반복 동시 게시·같은 링크·신생 계정 같은 <u>행동</u>만 본다. 일반 사용자는 집계로만 보인다.</span></div>
      <div class="pr"><b>군은 외국발 서사에만</b><span>외국어 출처가 연결되지 않은 서사는 조정 행위가 있어도 "국내 사안 — 군 관할 아님"에서 멈춘다. 국내 여론 감시 도구가 되지 않도록 규칙으로 막는다.</span></div>
      <div class="pr"><b>판정이 아니라 보조</b><span>모든 경보에 근거·신뢰도·하지 말 것을 함께 낸다. 분석관이 뒤집으면 근거를 다시 세고, 그 판정은 체인에 남는다.</span></div>
     </div>
     <div style="font-size:11.5px;color:var(--muted)">모든 숫자는 합성 72시간 시나리오의 자체 측정값(공개 IRA 실데이터·실제 공개 담화는 7단계) · 계정·매체는 전부 가상 · 실존 개인 식별·표적화 기능 없음</div></div>`;
  }
  else if(S.id==="flow"){
    if(FLOWVIEW==="graph"&&D.graph){
      if(!GRAPH||!document.getElementById("gcv")){killGraph();
        B.innerHTML=`<div class="gwrap fade"><canvas id="gcv"></canvas><div class="gtog"><button class="btn pri" onclick="FLOWVIEW='graph';renderStage()">그래프 뷰</button><button class="btn" onclick="FLOWVIEW='time';killGraph();renderStage()">시간축 뷰</button><button class="btn" onclick="go(1)" title="0시부터 72시까지 다시 재생">↻ 처음부터 재생</button><button class="btn" onclick="GRAPH&&GRAPH.fit()" title="화면 맞춤">⤢ 화면 맞춤</button></div><div class="ghud" id="ghud"></div><div class="gtip"></div><div class="gnote">점 = 계정(일반 사용자는 이름표 없음) · 선 = 리포스트·답글 / 초록 점선 = 외국어 원문 링크 공유 / 주황 = 반복 동시 게시로 묶임 · 드래그 이동 · 휠 확대</div></div>`;
        GRAPH=makeGraph(document.getElementById("gcv"),D.graph,flowHud);GRAPH.warm(h);GRAPH.start()}
      else GRAPH.seek(h);
      flowHud(GRAPH.counts(),h)}
    else{killGraph();B.innerHTML=`<div class="fade" style="height:100%;position:relative"><div class="gtog" style="z-index:2"><button class="btn" onclick="FLOWVIEW='graph';renderStage()">그래프 뷰</button><button class="btn pri" onclick="FLOWVIEW='time';renderStage()">시간축 뷰</button></div><div id="v1" class="plot"></div></div>`;chartFlow("v1",h,HH)}}
  else if(S.id==="watch"){
    B.innerHTML=`<div class="g2 fade"><div class="box"><div class="bt">시간당 게시물 — 회색 띠 = 10분 안 동시 게시(burst)</div><div class="bc" style="padding:0 4px 4px"><div id="v1" class="plot"></div></div></div>
     <div class="box"><div class="bc" style="padding:12px 14px" id="rside">${watchSide(h)}</div></div></div>`;
    chartVolume("v1",h,HH-34);
  }
  else if(S.id==="alert"){
    B.innerHTML=`<div class="g2 fade"><div class="box"><div class="bt">일반 사용자 간 R̂ — 파란 띠 = 80% 구간 · 주황 영역 = 경보 기준</div><div class="bc" style="padding:0 4px 4px"><div id="v1" class="plot"></div></div></div>
     <div class="box"><div class="bc" style="padding:12px 14px" id="rside">${alertSide(h)}</div></div></div>`;
    chartR("v1",h,HH-34);
  }
  else if(S.id==="pre"){
    if(!D.pre){B.innerHTML='<div class="mean">전조 카드 데이터 없음</div>';return}
    B.innerHTML=`<div class="g2 fade"><div class="box"><div class="bc" style="padding:4px 4px"><div id="v1" class="plot"></div></div></div>
     <div class="box"><div class="bc" style="padding:12px 14px" id="rside">${preSide(h)}</div></div></div>`;
    chartPre("v1",h,HH-10);
  }
  else if(S.id==="fa"){
    const narr=M.narr||{},ids=Object.keys(narr).sort((a,b)=>(narr[b].n_posts-narr[a].n_posts));
    const rows=ids.map(k=>{const v=narr[k],camp=k===CAMP;const ours=v.max_level;return `<tr style="${camp?"background:var(--row-hl)":""}"><td style="white-space:nowrap"><b>N${k}</b>${camp?'<div style="font-size:9.5px;color:var(--sus)">공작</div>':""}</td><td style="color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(v.sample.slice(0,22))}…</td><td style="text-align:right">${v.n_posts.toLocaleString()}</td><td style="white-space:nowrap">${v.vh==null?'<span style="color:#1baf7a">—</span>':`<span style="color:${camp?"#1baf7a":"#d03b3b"}">${v.vh}시${camp?"":" 오경보"}</span>`}</td><td style="white-space:nowrap"><span style="color:${LV[ours][1]};font-weight:700">${LV[ours][0]} ${ours==="NONE"?"없음":LV[ours][2]}</span>${v.pol_first&&!camp&&v.pol_first.includes("국내")?`<div style="font-size:9.5px;color:var(--muted)">국내 사안</div>`:""}</td></tr>`}).join("");
    const R=D.red,cv=R?Object.fromEntries(R.rows.map(r=>[r[0],r])):null;
    B.innerHTML=`<div class="g11 fade"><div class="box"><div class="bt">서사별 결과 — 단순 볼륨 감시(시간당 20건·중앙값 3배)와 우리 단계</div><div class="bc">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 10px"><div class="kp"><div class="l">정상 서사 ${FA.other_narratives||6}개 중 경보</div><div class="v">${FA.reached_watch_or_higher||0}<small>건</small></div><div class="n">팬덤의 합의된 동시 게시는 '검토 권장'에서 멈추고, 외국 출처가 없어 '국내 사안'</div></div><div class="kp"><div class="l">볼륨 감시가 공작 서사를 잡은 시각</div><div class="v">${TM.volume_alarm_h||8}시<small>우리 관찰 ${W_H}시</small></div><div class="n">더 빠르지만 정상 서사에도 울린다 — 강점은 속도가 아니라 구분력</div></div></div>
      <table class="tbl" style="font-size:11.5px;table-layout:fixed"><colgroup><col style="width:50px"><col><col style="width:52px"><col style="width:70px"><col style="width:104px"></colgroup><tr><th>서사</th><th>예시</th><th style="text-align:right">게시물</th><th>볼륨 감시</th><th>우리 최고 단계</th></tr>${rows}</table></div></div>
     <div class="box"><div class="bt">회피 내성 — 공격자 정교함 7단계에 따른 공작 계정 재현율 (합성 레드팀 · 시드 3 평균)</div><div class="bc" style="padding:0 4px"><div id="v2" class="plot"></div></div>
      ${cv?`<div style="padding:6px 12px 10px;font-size:12px;color:var(--muted)">시각 ±20분이면 burst <b>${cv.jitter20[2].toFixed(2)}</b>, ±60분 <b>${cv.jitter60[2].toFixed(2)}</b> · URL-망은 <b>${cv.base[3].toFixed(2)}</b> 유지, 뉴스 사칭형 <b>${cv.newsfeed[3].toFixed(2)}</b> — 그러나 인기 링크 희석 <b>${cv.newsfeed_mix[3].toFixed(2)}</b>, 고유 단축 URL <b>${cv.newsfeed_uniq[3].toFixed(2)}</b>. IRA 실데이터에서 URL-망의 추가 이득은 0.</div>`:""}</div></div>`;
    if(R)chartRed("v2",HH-100);
  }
  else if(S.id==="duel"){
    const U=D.duel;if(!U){B.innerHTML='<div class="mean" style="padding:20px">실험 4 결과 파일 없음 (experiments/out/exp4_decay_sigma.csv)</div>';}
    else{const row=U.rows.find(r=>r.sigma===SIG)||U.rows[0];const pct=v=>v==null?"—":Math.round(v*100)+"%";
      const meter=(v,c)=>`<div style="height:14px;background:var(--row-hl);border-radius:7px;overflow:hidden"><div style="width:${Math.round((v||0)*100)}%;height:100%;background:${c};transition:width .5s"></div></div>`;
      const st=U.stance||[];
      B.innerHTML=`<div class="g11 fade"><div class="box"><div class="bt">공격자: 게시 시각을 ±σ분 흩뜨린다 — <span style="color:var(--muted);font-weight:400">누르면 바뀝니다</span></div><div class="bc">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 12px">${U.rows.map(r=>`<button class="btn ${r.sigma===SIG?"pri":""}" style="padding:4px 10px" onclick="SIG=${r.sigma};renderStage();renderPanel();renderRail()">±${r.sigma}분</button>`).join("")}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div class="kp"><div class="l">burst 층 (10분 고정 창)</div><div class="v" style="color:${U.colors.burst}">${pct(row.burst)}</div>${meter(row.burst,U.colors.burst)}<div class="n">공작 계정 재현율 · 정밀도 ${row.burst_p==null?"—":row.burst_p.toFixed(2)}</div></div>
        <div class="kp"><div class="l">제3 신호층 (창 없음 · 시간 감쇠 다층)</div><div class="v" style="color:${U.colors.decay}">${pct(row.decay)}</div>${meter(row.decay,U.colors.decay)}<div class="n">정밀도 ${row.decay_p.toFixed(2)} · 정상 계정 오탐 ${row.organic} · 자동 선택 τ: URL ${row.tau_url}분</div></div></div>
        <div style="font-size:12px;color:var(--muted);margin-top:10px">창을 두지 않고 <b>같은 URL·거의 같은 문장·같은 뿌리 리포스트</b>에 시간 간격 감쇠 exp(−Δt/τ)를 곱해 쌓는다. 시각을 무작위로 섞은 대조군 20회의 상위 1%를 1로 정규화 → 우연으로는 안 나오는 연결만 남기고, 군집이 <b>서로 다른 시간대 2곳 이상</b>에서 함께 움직여야 의심(팬덤의 1회 합의 동시 게시는 '검토'). 흩뜨리지 않으면 burst 층이 더 좋다(0.90 vs 0.80) → <b>두 층을 같이 쓴다</b>.</div></div></div>
       <div class="box"><div class="bt">두 층의 생존 곡선 (실험 4, 합성 · 시드 3 평균)</div><div class="bc" style="padding:0 4px"><div id="v2" class="plot"></div></div>
        ${st.length?`<div style="padding:6px 12px 10px;font-size:12px;color:var(--muted)"><b>입장 판별 층(R̂ 두 줄)</b> — 반박 답글을 걸러내면 경보 시각이 늦어진다: ${st.map(x=>`반박 ${Math.round(x.ratio*100)}% → 전체 ${x.alert_all}시 / 찬성만 <b>${x.alert_support}</b>시`).join(" · ")} (실험 5, 규칙 백엔드 · 정확도는 손 라벨 전까지 미측정). <b>사이트 층</b>(도메인 일괄 등록·공유 IP·인증서 묶음·동일 테마)은 설계·점검 완료, 외부 조회는 맥에서 실행.</div>`:""}</div></div>`;
      chartDuel("v2",HH-120);}
  }
  else if(S.id==="real"){
    const R=D.real,RP=D.replay,s2=RP?RP.summary[RPTAG]:null;
    B.innerHTML=`<div class="g11 fade"><div class="box"><div class="bt">공개 IRA 트윗 ${R?R.tweets.toLocaleString():""}건 · ${R?R.window:""} · 같은 규칙(10분 안 같은 글·같은 링크, 2회 이상)</div><div class="bc">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:4px 0 8px">${R?[["동시 게시 묶음",R.events.toLocaleString(),`시각 무작위 이동 대조군 ${Math.round(R.null_events_mean)}건 → 약 ${Math.round(R.events/R.null_events_mean)}배`],["같은 운영팀 비율",(R.same_category_rate*100).toFixed(1)+"%",`무작위면 ${Math.round(R.same_category_rate_random*100)}%`],["반복 참여 계정",Math.round(R.accounts_repeated_share*100)+"%",`${R.accounts}개 계정 중`]].map(([l,v,n])=>`<div class="kp"><div class="l">${l}</div><div class="v" style="font-size:21px">${v}</div><div class="n">${n}</div></div>`).join(""):""}</div>
      <div style="font-size:12px;color:var(--muted);margin:2px 0 0">운영팀별 '반복 동시 게시' 계정 비율 — 뉴스 매체 사칭은 <b>0%</b>(각자 시간에 게시 · URL-망 층도 못 잡음)</div><div id="v1" class="plot" style="height:${Math.max(160,HH-210)}px"></div></div></div>
     <div class="box"><div class="bt">실제 공개 담화 ${RP?RP.cases.length:0}건에 같은 규칙을 돌리면 — <button class="btn" style="padding:2px 8px;font-size:11px" onclick="RPTAG=RPTAG==='v2'?'v1':'v2';renderStage()">${RPTAG==="v2"?"v2 (실제 담화 보고 고침)":"v1 (합성 문장만 보고 만듦)"} ↔</button></div><div class="bc" style="padding:0 4px"><div id="v2" class="plot" style="height:${Math.max(180,HH-150)}px"></div>
      ${s2?`<div style="padding:4px 10px 8px;font-size:12px;color:var(--muted)">${RPTAG}: 행동으로 이어진 ${s2.n_precedent}건 중 L3 선행 <b>${s2.n_hit}건</b>(${s2.leads.map(x=>x+"일").join("·")}), 행동 없던 ${s2.n_false_alarm_cases}건 중 L3 <b>${s2.n_false_alarm_l3}건</b> → 공식 축 단독이면 오경보 ${s2.n_false_alarm_l3}/${s2.n_false_alarm_cases}. in-sample 작동 확인 · 정확도 주장 아님.</div>`:""}</div></div>`;
    if(R)chartIRA("v1",Math.max(160,HH-210));if(RP)chartReplay("v2",Math.max(180,HH-150),RPTAG);
  }
  else if(S.id==="human"){
    const rr=rowAt(h),pr=polAt(h),ex=JUDGED?new Set([N.bursts[0]?N.bursts[0].id:0]):new Set();
    const before=Object.entries(N.joined).filter(([,t])=>t<=h).length,after=JUDGED?Object.keys(N.ab).filter(a=>isSusAt(+a,h,ex)).length:before;
    const fo=N.foreign.filter(f=>f.x<h),met=after>=(D.an.min_susp||5)&&fo.length>0,bb=N.bursts.filter(b=>b.e<h);
    const rec=JUDGED?judgeRecord():null;
    const brief=[`# 브리핑 초안 — 서사 N${CAMP} · ${fmt(h)} (시작 후 ${h}시)`,`시스템 생성 초안(규칙 기반 템플릿 · LLM 미사용) · 분석관 검토 전`,``,`## 1. 요약`,`- 단계 ${rr.level} · 권고 ${pr?pr.al:"—"}`,`- 외국어 원문 ${fo.length}건 · burst ${bb.length}회 · 의심 계정 ${after}개${JUDGED?` (판정 전 ${before})`:""}`,D.pre?`- 전조 정합성 ${preRow(h).state_label} (${preRow(h).conv}/3축)`:``,`## 2. 근거`,...bb.slice(0,3).map((b,i)=>`- ${b.start}–${b.end} · 계정 ${b.n}개 · 유사도 ${b.sim.toFixed(2)}${JUDGED&&i===0?" · 분석관 판정: 정상(속보 동기화)":""}`),`- R̂ ${rr.r==null?"—":rr.r.toFixed(2)} · P(R>1) ${rr.p1==null?"—":Math.round(rr.p1*100)+"%"}`,`## 3. 권고와 하지 말 것`,`- ${pr?pr.al:"—"} — ${pr?pr.lvl:""}`,`- 하지 말 것: ${pr?pr.dn.join(" / "):"—"}`,`## 4. 분석관 판정 반영`,JUDGED?`- burst 1 → 정상 · 기록 ${rec.record_sha256.slice(0,12)}… (증거 체인 끝 ${D.an.chain_end.slice(0,8)}…에 연결)`:`- 판정 없음`].filter(x=>x!==``||true).join("\n");
    B.innerHTML=`<div class="g3 fade">
     <div class="box"><div class="bt">① 분석관 판정 — 이 burst는 정상인가?</div><div class="bc" style="padding:10px 12px">
      ${bb.slice(0,4).map((b,i)=>`<div style="font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--line)"><b>burst ${i+1}</b> ${b.start}–${b.end} · 계정 ${b.n}개 · 같은 링크${i===0&&JUDGED?` · <span style="color:${CC().ord};font-weight:700">판정: 정상(속보 동기화)</span>`:""}</div>`).join("")}
      <div style="margin:10px 0 6px"><button class="btn ${JUDGED?"":"pri"}" onclick="JUDGED=!JUDGED;renderStage();renderPanel()">${JUDGED?"판정 되돌리기":"burst 1을 '정상(속보 동기화)'으로 판정"}</button></div>
      <div class="kp"><div class="l">의심 계정 재집계</div><div class="v">${before}<small>→</small> <span style="color:${CC().ord}">${after}</span></div><div class="n">${JUDGED?(met?"관찰 조건(5개 이상 + 외국어 출처) 유지 · 경보 단계는 R̂가 정하므로 그대로":"관찰 조건 미충족 → 단계 해제 검토 (자동 하향 없음 — 해제는 분석관)"):"판정 없음 — 시스템 근거 그대로"}</div></div>
      ${JUDGED?`<div style="font-size:12px;margin-top:8px">✅ 판정 기록 1건 · SHA-256 <code>${rec.record_sha256.slice(0,16)}…</code><br><span style="color:var(--muted)">증거 체인 끝 <code>${D.an.chain_end.slice(0,12)}…</code>에 이어 붙임 · 역할은 가명 · 지우거나 바꾸면 해시가 달라진다</span></div>`:`<div style="font-size:12px;color:var(--muted);margin-top:8px">판정하면 그 burst를 근거에서 빼고 다시 센다. 시스템 숫자를 덮어쓰지 않고, 판정 자체가 증거 체인에 남는다.</div>`}
     </div></div>
     <div class="box"><div class="bt">② 지휘관 화면 — 같은 데이터를 줄인 한 장</div><div class="bc" style="padding:10px 12px">
      <div style="font-size:17px;font-weight:700;margin-bottom:8px">N${CAMP} · ${rr.level} ${LV[rr.level][2]} · ${pr?esc(pr.al):"권고 없음"}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">${[["의심 계정",`${after}개`],["외국어 선행",fo.length?`${fo.length}건`:"없음"],["P(R>1)",rr.p1==null?"—":Math.round(rr.p1*100)+"%"],["전조 정합성",D.pre?preRow(h).state_label:"—"]].map(([l,v])=>`<div class="kp"><div class="l">${l}</div><div class="v" style="font-size:20px">${v}</div></div>`).join("")}</div>
      ${pr&&pr.dn.length?`<div style="margin-top:10px;font-size:12.5px"><b>하지 말 것</b> — ${pr.dn.map(esc).join(" · ")}</div>`:""}
      <div style="margin-top:6px;font-size:12.5px"><b>다음 재평가</b> — ${pr?esc(pr.esc):"—"}</div>
      <div style="margin-top:10px;font-size:11.5px;color:var(--muted)"><b>운용 위치</b> ${esc(D.an.conops["위치"])}<br><b>경계</b> ${esc(D.an.conops["경계"])}</div>
     </div></div>
     <div class="box"><div class="bt">③ 브리핑 초안 — LLM 없이 카드 필드로만 (숫자가 화면과 항상 같다)</div><div class="bc"><div class="mono">${esc(brief)}</div></div></div></div>`;
  }
}
// 판정 기록 해시 (sha256 · 화면 안 검증용)
function sha256(str){const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  let H0=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];const b=new TextEncoder().encode(str);const l=b.length;const n=((l+9+63)>>6)<<6;const m=new Uint8Array(n);m.set(b);m[l]=0x80;const dv=new DataView(m.buffer);dv.setUint32(n-4,(l*8)>>>0);dv.setUint32(n-8,Math.floor(l*8/4294967296));
  const w=new Uint32Array(64);const rr=(x,k)=>(x>>>k)|(x<<(32-k));
  for(let i=0;i<n;i+=64){for(let t=0;t<16;t++)w[t]=dv.getUint32(i+t*4);for(let t=16;t<64;t++){const s0=rr(w[t-15],7)^rr(w[t-15],18)^(w[t-15]>>>3),s1=rr(w[t-2],17)^rr(w[t-2],19)^(w[t-2]>>>10);w[t]=(w[t-16]+s0+w[t-7]+s1)>>>0}
    let [a,bb,c,d,e,f,g,h]=H0;for(let t=0;t<64;t++){const S1=rr(e,6)^rr(e,11)^rr(e,25),ch=(e&f)^(~e&g),t1=(h+S1+ch+K[t]+w[t])>>>0,S0=rr(a,2)^rr(a,13)^rr(a,22),mj=(a&bb)^(a&c)^(bb&c),t2=(S0+mj)>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=bb;bb=a;a=(t1+t2)>>>0}
    H0=[a,bb,c,d,e,f,g,h].map((x,k)=>(x+H0[k])>>>0)}
  return H0.map(x=>x.toString(16).padStart(8,"0")).join("")}
let _REC=null;function judgeRecord(){if(_REC)return _REC;const body={kind:"analyst_judgment",narrative_id:+CAMP,hour:H,burst_id:N.bursts[0]?N.bursts[0].id:0,judgment:"normal",role:D.an.role,recorded_at:new Date().toISOString().slice(0,19)+"Z",prev:D.an.chain_end};body.record_sha256=sha256(JSON.stringify(body));_REC=body;return body}
// ---------------------------------------------------------------- 오른쪽 설명 패널
function panelData(){
  const S=STEPS[STEP],h=H,rr=rowAt(h),pr=polAt(h);
  const kp=(l,v,n)=>({l,v,n});
  if(S.id==="why")return{head:"지금 보는 것 — 전체 그림",kpis:[kp("관찰 → 경보 → 위험",`${W_H} · ${A_H} · ${C_H}시`,"72시간 가상 공작 시나리오 안에서"),kp("공작 계정 탐지",`정밀도 ${CB.precision??"—"} · 재현율 ${CB.recall??"—"}`,"정상 사용자 오탐 0 (합성 자체 측정)"),kp("정상 서사 오경보",`${FA.other_narratives||6}개 중 ${FA.reached_watch_or_higher||0}`,"팬덤·속보·잡담은 경보로 올라가지 않는다")],
    mean:`외국에서 만든 이야기가 한국 시민의 말이 되면 그때부터 "외국 공작"이라고 말하기 어려워진다 — 대응하는 순간 국민의 표현을 공격하는 모양이 되기 때문이다. 그래서 이 도구는 <b>"공작인가"</b>보다 <b>"지금 대응해도 되는가, 어떻게 해야 하는가"</b>를 묻는다. 위 여섯 칸이 데이터가 지나가는 길이고, 아래 세 원칙이 설계의 출발점이다.`,
    lim:"합성 데이터의 자체 측정값이다. 오탐률·조기성은 실데이터에서 아직 검증되지 않았다 — 7단계에서 실데이터와 실제 담화로 확인한 범위를 그대로 보여준다.",
    note:"외국에서 만든 이야기가 한국 시민의 말이 되는 순간, 그때부터는 외국 공작이라고 말하기 어려워집니다. 그래서 저는 '공작인가'보다 '지금 대응해도 되는가, 어떻게 해야 하는가'를 묻는 분석관 보조 도구를 만들었습니다. 핵심은 두 가지 — 내용이 아니라 행동을 보고, 군은 외국발 서사에만 손을 댑니다."};
  if(S.id==="flow"){const fo=N.foreign.filter(f=>f.x<h),koX=N.posts.filter(p=>p[3]==="ko"&&p[0]<h).map(p=>p[0]),firstKo=koX.length?Math.min(...koX):null,lead=fo.length&&firstKo!=null?Math.max(...fo.map(f=>firstKo-f.x)):null,bb=N.bursts.filter(b=>b.e<h);
    return{head:"지금 보는 것 — 확산 경로",kpis:[kp("외국어 원문",`${fo.length}건`,fo.length?fo.map(f=>f.lang).join(" · ")+" 가상 매체 기사":"아직 없음"),kp("한국어 첫 게시",firstKo!=null?`${fmt(firstKo)}`:"아직",lead!=null?`외국어 원문보다 ${lead.toFixed(1)}시간 뒤`:"—"),kp("동시 게시 burst",`${bb.length}회`,bb.length?`${bb[0].n}개 계정이 ${bb[0].start.slice(6)}부터 10분 안에 같은 링크`:"아직 없음")],
    mean:`초록 점은 외국어 원문, 주황은 반복 동시 게시가 확인된 <b>가명 계정</b>, 파랑은 <b>일반 사용자의 집계</b>다. 일반 사용자는 개별 계정으로 그리지 않는다 — 같은 주장을 했다는 이유로 시민을 지목하지 않기 위해서다. 세로축은 외국어 원문에서 몇 단계 떨어졌는가다.`,
    lim:"서사 묶기는 다국어 임베딩(공개 모델)이며, 짧은 구어체 한국어에서는 주제보다 문체를 반영해 링크 없는 같은 주장은 놓칠 수 있다.",
    note:"지금은 시작 후 13시입니다. 중국어·러시아어·일본어·영어 가상 매체 기사 4건이 먼저 나왔고, 한국어 첫 글보다 7.5시간 앞섭니다. 신생 계정 20개가 10분 안에 같은 링크와 거의 같은 문장을 올렸고, 이런 일이 두 번 반복됐습니다."}}
  if(S.id==="watch"){const said=saidAt(h),nBeh=[...said].filter(a=>isSusAt(a,h)).length;
    return{head:`지금 보는 것 — ${h}시 관찰 단계`,kpis:[kp("단계",`${LV[rr.level][0]} ${rr.level} ${LV[rr.level][2]}`,"의심 계정 5개 이상 + 외국어 출처 연결"),kp("의심 계정 (행동 기준)",`${nBeh}<small>내용 기준이면 ${said.size}</small>`,"같은 주장을 하는 시민을 공작으로 몰지 않는다"),kp("권고",pr?pr.al:"—",pr?pr.lvl:"")],
    mean:`관찰은 확산과 무관하게 <b>행동 + 외국 출처</b>만으로 울리는 조기 신호다. 시뮬레이션 세계에서 일반 시민 사이 확산이 실제로 1을 넘는 건 약 <b>${TM.generator_param_cross_1_h?Math.round(TM.generator_param_cross_1_h):37}시</b>이니 약 하루 먼저 본 셈이다. 권고는 "준비"다 — 아무도 안 보는 이야기를 우리가 키울 수 있으니 아직 공개 대응은 하지 말라는 뜻이다.`,
    lim:`공작 계정 ${CB.campaign_review??3}개는 burst에 1회만 참여해 '검토 권장'에 머물렀다(미탐). 경보 시각은 설정에 민감하다(26~55시) — 운영 정책으로 정할 값.`,
    note:"그래서 관찰 단계가 떴습니다. 권고는 '사전 반박 준비' — 아직 공개 대응은 하지 말라고 합니다. 만약 내용으로 판단하면 이 이야기를 말한 계정 전부가 의심 대상이 되지만, 행동으로 보면 열 개만 남습니다. 이게 설계의 출발점입니다."}}
  if(S.id==="alert")return{head:`지금 보는 것 — ${h}시 경보 단계`,kpis:[kp("P(R > 0.8)",rr.p08==null?"—":Math.round(rr.p08*100)+"%","경보 = 50% 이상 (점추정이 아니라 사후확률)"),kp("권고",pr?pr.al:"—","출처 근거가 아직 선명한 마지막 구간"),kp("증거 봉인",D.seal.ok?"검증 통과":"검증 실패",esc(D.seal.msg))],
    mean:`파란 띠는 80% 구간이고, 경보는 <b>R이 0.8을 넘을 확률이 50%</b>를 넘을 때 올린다. 이때 본 게시물은 전체의 약 10%다. 권고가 "사전 반박 <b>실행 검토</b>"로 올라간다 — 수법 공개 중심의 사전 반박 문안을 내보낼지 결정하라는 뜻이고, 결정은 사람이 한다. 근거 카드에는 DISARM 후보 기법 코드도 붙어 해외 분석관과 같은 분류 체계로 공유할 수 있다.`,
    lim:"R̂는 6시간 창 때문에 늦게 잡히고 표본이 적으면 출렁인다. 반박·팩트체크 답글도 같은 서사로 묶여 확산으로 집계될 수 있어 상한값으로 읽어야 한다.",
    note:"41시가 되면 일반 시민 사이 재생산수가 1에 가까워집니다. R이 0.8을 넘을 확률이 59%, 이때 권고가 '사전 반박 실행 검토'로 올라갑니다. 지금이 출처 근거가 아직 선명한 마지막 구간이라는 뜻입니다."};
  if(S.id==="pre"){const row=preRow(h),sm=D.pre?D.pre.summary:{};
    return{head:`지금 보는 것 — 전조 카드 (${h}시)`,kpis:[kp("정합성",`${PST[row.state][0]} ${row.state_label}`,`수렴 ${row.conv}/3축`),kp("공식 예고 → 은밀 증폭 관찰",`${Math.round(sm.a_first_level3_h)}시 → ${sm.c_first_watch_h}시`,`발언 ${sm.a_first_level3_id} 뒤 ${Math.round(sm.a_to_watch_h)}시간`),kp("불일치 시작",`${sm.first_mismatch_h}시`,"완화 담화가 나오는데 은밀 증폭은 상승")],
    mean:`회색지대 도발은 행동 전에 <b>말이 먼저 준비</b>된다는 가설을 네 축으로 나눴다. 공식 발언은 양이 아니라 <b>구조</b>(조건·시한·장소·수단·톤)를 뽑고, 공식 축만으로는 절대 경보하지 않는다(기만·동시 선전 반례). 말이 부드러워지는데 은밀 증폭이 오르면 <b>불일치</b> — "완화 발언을 근거로 경계를 낮추지 말 것"이 하지 말 것에 추가된다.`,
    lim:"축 A·B 자료는 가상(합성)이고 추출은 규칙 기반이다(운용 시 LLM 교체, 인용 구절 검증은 유지). 사례 라이브러리는 참고용이며 L5(국가 배후)는 공개 데이터로 판단 불가로 고정.",
    note:"도발은 행동 전에 말이 먼저 준비됩니다. 11시 담화에 조건·시한·장소가 함께 들어왔지만 그것만으로는 수사 단독, 경보하지 않습니다. 13시 은밀 증폭이 관찰에 들어서며 수렴이 되고, 47시엔 '대화의 문' 완화 담화가 나오는데 증폭은 오르고 있죠 — 불일치입니다."}}
  if(S.id==="fa"){const R=D.red,cv=R?Object.fromEntries(R.rows.map(r=>[r[0],r])):null;
    return{head:"지금 보는 것 — 오경보와 회피",kpis:[kp("정상 서사 오경보",`${FA.other_narratives||6}개 중 ${FA.reached_watch_or_higher||0}`,"볼륨 감시는 N2(팬덤)에도 울린다"),kp("시각 ±20분 분산 시 burst 재현율",cv?`${cv.base[2].toFixed(2)} → ${cv.jitter20[2].toFixed(2)}`:"—","±60분이면 0 — 측정했고 그대로 적었다"),kp("제2 신호층(URL-망)",cv?`${cv.base[3].toFixed(2)} 유지`:"—",cv?`뉴스 사칭형 ${cv.newsfeed[3].toFixed(2)} · 희석·단축 URL이면 ${cv.newsfeed_mix[3].toFixed(2)}`:"")],
    mean:`단순히 게시량만 보면 더 빨리(${TM.volume_alarm_h||8}시) 울리지만 팬덤이 섞인 국내 서사에도 똑같이 울린다. 우리의 강점은 속도가 아니라 <b>구분력</b>이다. 회피는 레드팀으로 쟀다 — 시각을 흩뜨리면 burst 층은 무너지고, 시각과 무관한 <b>URL 공유 네트워크</b> 층이 절반을 받친다. 그러나 인기 링크 희석·고유 단축 URL이면 그 층도 0이다.`,
    lim:"레드팀은 합성(서사 배정은 정답 고정 · burst 층에 유리한 조건). IRA 실데이터에서 URL-망의 추가 이득은 0이었다 — 뉴스 사칭 계정은 bit.ly 단축 주소에 도시별 미러링이라 '같은 링크'가 성립하지 않는다.",
    note:"볼륨만 보면 8시에 더 빨리 울리지만 정상 서사에도 울립니다. 우리는 정상 서사 6개 중 0개에 경보를 냈습니다. 회피도 쟀습니다 — 시각을 20분만 흩뜨려도 재현율이 0.9에서 0.24로 떨어지고, 시각과 무관한 제2 층이 0.63으로 받칩니다. 단 단축 URL이면 그것도 0입니다. 그대로 보여드립니다."}}
  if(S.id==="duel"){const U=D.duel,row=U?(U.rows.find(r=>r.sigma===SIG)||U.rows[0]):null,b0=U?U.rows[0]:null;
    return{head:`지금 보는 것 — 회피 대결 (±${SIG}분)`,kpis:[kp("burst 층 재현율",row?`${row.burst==null?"—":row.burst.toFixed(2)}`:"—",b0?`흩뜨리기 전 ${b0.burst.toFixed(2)}`:""),kp("제3 신호층 재현율",row?row.decay.toFixed(2):"—",b0?`흩뜨리기 전 ${b0.decay.toFixed(2)} · 정밀도 1.0 유지`:""),kp("정상 계정 오탐",row?`${row.organic}`:"—","팬덤은 '검토'에 머묾")],
    mean:`실험 2a에서 드러난 가장 큰 사각지대가 <b>시간 분산</b>이었다. 그래서 창을 없앴다. 2025년 12월 선례(시간 감쇠 다층 협업 가중치, 26개 정보작전 데이터셋 검증)를 따르되 τ는 <b>시각 셔플 대조군을 넘는 연결이 가장 많이 남는 값</b>으로 층마다 자동 선택한다 — 공격자가 흩뜨릴수록 τ가 길어진다. 실제 공작의 조정 간격은 '몇 시간'(OpenAI 2026-06 보고서)이라 이 층이 운용에선 기본이 된다.`,
    lim:"합성 데이터(서사 배정 고정). 흩뜨리지 않으면 burst 층보다 낮다(0.80 vs 0.90). ±120분이면 이 층도 0.18. 실데이터(IRA)에는 아직 안 돌렸다. 시연 숫자(13·41·56시)는 burst 층 기준 그대로다.",
    note:"공격자가 시각을 20분만 흩뜨리면 기존 층은 0.18로 무너집니다. 그래서 창을 없앤 제3 층을 더했습니다 — 같은 20분에 0.77, 60분에도 절반을 지킵니다. 정밀도는 1.0, 정상 계정 오탐은 0입니다. 흩뜨리지 않으면 기존 층이 더 좋으니 둘을 같이 씁니다."}}
  if(S.id==="real"){const R=D.real,RP=D.replay,s2=RP?RP.summary.v2:null,s1=RP?RP.summary.v1:null;
    return{head:"지금 보는 것 — 실데이터 · 실제 담화",kpis:[kp("IRA 동시 게시 묶음",R?`${R.events.toLocaleString()}<small>vs 대조군 ${Math.round(R.null_events_mean)}</small>`:"—",R?`약 ${Math.round(R.events/R.null_events_mean)}배 · 묶인 계정 같은 팀 ${(R.same_category_rate*100).toFixed(1)}%`:""),kp("실제 담화 — 합성 기준 규칙(v1)",s1?`선행 ${s1.n_hit}/${s1.n_precedent}`:"—","합성 데이터 과적합 그대로"),kp("실제 담화 — 고친 규칙(v2)",s2?`선행 ${s2.n_hit}/${s2.n_precedent} · 오경보 ${s2.n_false_alarm_l3}/${s2.n_false_alarm_cases}`:"—","공식 축 단독이면 오경보 — 정합성이 필요한 이유")],
    mean:`실제 공작 계정도 <b>동시 게시 흔적</b>을 남긴다 — 시각을 무작위로 섞은 대조 실험보다 약 400배 많았고, 묶인 계정의 99.9%가 같은 운영팀이었다. 전조 카드 규칙은 실제 공개 담화 10건에 돌려 봤다: 합성 문장만 보고 만든 규칙은 무너졌고, 고친 규칙은 선행은 잡지만 행동 없던 사례도 잡는다. 그래서 <b>공식 축 단독으로는 경보하지 않는다</b>.`,
    lim:"IRA 검증은 공작 계정끼리의 동기화 확인이지 일반인 대비 오탐률이 아니다(2016 미국 대상). 실제 담화 결과는 10문장을 모두 본 뒤 고친 in-sample 작동 확인이며 사례가 적어 정확도를 주장하지 않는다.",
    note:"공개된 러시아 IRA 트윗 약 20만 건에 같은 규칙을 적용하니 동시 게시가 대조 실험보다 약 400배 많았고, 묶인 계정의 99.9%가 같은 운영팀이었습니다. 전조 규칙은 실제 담화에서 처음엔 무너졌고, 고친 뒤에도 공식 발언만으론 오경보가 납니다. 그래서 정합성입니다."}}
  if(S.id==="human"){const before=Object.entries(N.joined).filter(([,t])=>t<=h).length;
    return{head:"지금 보는 것 — 사람이 결정한다",kpis:[kp("분석관 판정",JUDGED?"1건 기록":"없음",JUDGED?`의심 ${before} → 재집계 · 체인 연결`:"burst 하나를 정상으로 판정해 보세요"),kp("단계 자동 하향","없음","'해제 검토'만 표시, 해제는 분석관"),kp("브리핑 초안","LLM 미사용","카드 필드로만 생성 → 숫자가 화면과 같다")],
    mean:`시스템은 판정하지 않는다. 분석관이 동시 게시 묶음 하나를 "정상(속보 동기화)"으로 판정하면 그 묶음을 빼고 <b>의심 집단과 관찰 조건을 다시 센다</b>. 판정은 증거 체인 끝 해시에 이어 SHA-256으로 기록되고 브리핑에 그대로 들어간다. 지휘관 화면은 같은 데이터를 숫자 3개·권고 1줄·하지 말 것으로 줄인 것이며 새 판단을 더하지 않는다.`,
    lim:"운용 위치는 외국발 유입 탐지까지. 국내 대응·플랫폼 조치·수사는 관계 기관 이관이며 기관별 법적 근거는 [확인 필요]. 다음 단계: 라벨된 연구용 데이터로 오탐률·조기성 검증, 단축 URL 해석기·WHOIS 연결, 사례 라이브러리 확대.",
    note:"운용은 외국발 서사 유입 탐지로 한정하고, 일반 시민은 집계로만 다룹니다. 분석관이 뒤집으면 근거를 다시 세고 그 판정이 체인에 남습니다. 다음 단계는 일반 사용자까지 라벨된 연구용 데이터로 오탐률과 조기성을 검증하는 것입니다. 감사합니다."}}
  return{head:"",kpis:[],mean:"",lim:"",note:""}}
function renderPanel(){const P=panelData();document.getElementById("panel").innerHTML=`<div class="hd">${P.head}</div>${P.kpis.map(k=>`<div class="kp"><div class="l">${k.l}</div><div class="v">${k.v}</div><div class="n">${k.n}</div></div>`).join("")}<div class="mean">${P.mean}</div><div class="lim"><b>한계</b> · ${P.lim}</div><div class="note"><b>발표 멘트</b> · ${P.note}</div>`}
// ---------------------------------------------------------------- 레일·푸터·진행
function renderRail(){const res=stepResult();document.getElementById("rail").innerHTML=`<div class="hd">진행 단계 — 클릭하면 이동 · 총 9단계 · 자동 재생 1분</div>`+STEPS.map((s,i)=>`<div class="st ${i===STEP?"on":""} ${i<STEP?"done":""}" onclick="go(${i})"><div class="n">${i<STEP?"✓":i+1}</div><div><div class="t">${s.short}</div><div class="s">${res[i]||""}</div></div></div>`).join("")}
function stepResult(){const r41=rowAt(A_H),cv=D.red?Object.fromEntries(D.red.rows.map(r=>[r[0],r])):null,s2=D.replay?D.replay.summary.v2:null;
  return[`합성 72h · ${(M.n_posts||0).toLocaleString()} 게시물`,`72시간 그래프 재생 · 외국어 ${N.foreign.length}건 → 가명 계정 → 집계`,`관찰 · 권고 '사전 반박 준비'`,`P(R>0.8) ${r41.p08==null?"—":Math.round(r41.p08*100)+"%"} · 실행 검토`,D.pre?`수렴 → 불일치 ${MM_H}시`:"",`정상 ${FA.other_narratives||6}개 중 ${FA.reached_watch_or_higher||0} · 회피 측정`,D.duel?`±20분: ${D.duel.rows.find(r=>r.sigma===20).burst.toFixed(2)} → ${D.duel.rows.find(r=>r.sigma===20).decay.toFixed(2)}`:"",`IRA 400배 · 담화 v1→v2`,`판정 → 재집계 · 체인 기록`]}
function renderFooter(){document.getElementById("hs").value=H;const marks=[[0,"0시"],[W_H,`${W_H} 관찰`],[A_H,`${A_H} 경보`],[MM_H,`${MM_H} 불일치`],[C_H,`${C_H} 위험`],[72,"72시"]];document.getElementById("marks").innerHTML=marks.map(([x,t])=>`<span style="left:${x/72*100}%">${t}</span>`).join("");
  const timeStep=["flow","watch","alert","pre","human"].includes(STEPS[STEP].id);document.getElementById("hs").disabled=!timeStep;document.getElementById("hs").style.opacity=timeStep?1:.35;
  document.getElementById("prev").disabled=STEP===0;document.getElementById("next").textContent=STEP===STEPS.length-1?"처음으로 ↺":"다음 ▶";document.getElementById("play").textContent=PLAYING?"⏸ 정지":"▶ 자동 재생 (1분)"}
function renderAll(){renderRail();renderStage();renderPanel();renderFooter()}
function stopAnim(){if(RAF)cancelAnimationFrame(RAF);RAF=null;if(PLAY_T)clearTimeout(PLAY_T);PLAY_T=null}
function animateHour(from,to,secs,done){stopAnim();const t0ms=performance.now();let last=-1;const tick=now=>{const k=Math.min(1,(now-t0ms)/(secs*1000));const hf=from+(to-from)*k,h=k>=1?to:Math.floor(hf);
  if(STEPS[STEP].id==="flow"&&FLOWVIEW==="graph"&&GRAPH){GRAPH.seek(hf);if(h!==last){last=h;H=h;renderPanel();renderFooter();document.getElementById("sclock").innerHTML=`관측 시각 (시작 후 ${h}시)<b>${fmt(h)}</b>`}}
  else{updateHour(hf);if(h!==last){last=h;H=h;renderPanel();renderFooter()}}
  if(k<1)RAF=requestAnimationFrame(tick);else{RAF=null;if(done)done()}};RAF=requestAnimationFrame(tick)}
function go(i,opts){stopAnim();killGraph();PREMODE="card";STEP=(i+STEPS.length)%STEPS.length;const S=STEPS[STEP];const anim=S.anim&&!(opts&&opts.noAnim);H=anim?S.anim[0]:S.hour;renderAll();if(anim)animateHour(S.anim[0],S.anim[1],(PLAYING||S.id==="flow")?S.anim[2]:Math.min(S.anim[2],6),null)}
function play(){if(PLAYING){PLAYING=false;stopAnim();renderFooter();setProg(0);return}PLAYING=true;renderFooter();const total=STEPS.reduce((s,x)=>s+x.dur,0);let elapsed=STEPS.slice(0,STEP).reduce((s,x)=>s+x.dur,0);const startAt=performance.now()-elapsed*1000;
  const prog=()=>{if(!PLAYING)return;setProg(Math.min(1,(performance.now()-startAt)/(total*1000)));requestAnimationFrame(prog)};prog();
  const runStep=()=>{if(!PLAYING)return;const S=STEPS[STEP];stopAnim();killGraph();H=S.anim?S.anim[0]:S.hour;renderAll();
    const after=()=>{if(!PLAYING)return;PLAY_T=setTimeout(()=>{if(STEP>=STEPS.length-1){PLAYING=false;renderFooter();setProg(0);return}STEP++;runStep()},Math.max(0,(S.dur-(S.anim?S.anim[2]:0))*1000))};
    if(S.anim)animateHour(S.anim[0],S.anim[1],S.anim[2],after);else after()};
  runStep()}
function setProg(k){document.querySelector("#prog i").style.width=(k*100)+"%"}
document.getElementById("prev").onclick=()=>{PLAYING=false;go(STEP-1)};document.getElementById("next").onclick=()=>{PLAYING=false;go(STEP+1)};document.getElementById("play").onclick=play;
document.getElementById("hs").oninput=e=>{stopAnim();PLAYING=false;H=+e.target.value;if(STEPS[STEP].id==="flow"&&FLOWVIEW==="graph"&&GRAPH){GRAPH.seek(H);flowHud(GRAPH.counts(),H);document.getElementById("sclock").innerHTML=`관측 시각 (시작 후 ${H}시)<b>${fmt(H)}</b>`;renderPanel();renderFooter()}else{updateHour(H);renderPanel();renderFooter()}};
document.getElementById("noteBtn").onclick=()=>{SHOWNOTE=!SHOWNOTE;document.body.classList.toggle("show-note",SHOWNOTE)};
document.getElementById("themeBtn").onclick=()=>{document.body.classList.toggle("light");document.getElementById("themeBtn").textContent=document.body.classList.contains("light")?"☾":"☀";renderStage();renderPanel()};
document.getElementById("fsBtn").onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen()};
window.addEventListener("keydown",e=>{if(e.target.tagName==="INPUT"&&e.target.type!=="range")return;if(e.key==="ArrowRight"){PLAYING=false;go(STEP+1)}else if(e.key==="ArrowLeft"){PLAYING=false;go(STEP-1)}else if(e.key===" "){e.preventDefault();play()}else if(e.key==="Escape"){PLAYING=false;stopAnim();renderFooter()}});
let RS=null;window.addEventListener("resize",()=>{clearTimeout(RS);RS=setTimeout(()=>{renderStage()},150)});
go(0,{noAnim:true});
</script></body></html>"""


def duel_payload():
    """2026-10-26: 실험 4(창 없는 제3 신호층 vs burst 층)·실험 5(입장 판별) 결과를 '회피 대결' 단계에 싣는다. 파일 없으면 None."""
    import pandas as pd
    p4 = os.path.join(HERE, "experiments/out/exp4_decay_sigma.csv"); p5 = os.path.join(HERE, "experiments/out/exp5_stance.csv")
    if not os.path.exists(p4):
        return None
    G = pd.read_csv(p4)
    rows = [dict(sigma=int(r.sigma), burst=(None if pd.isna(r.재현율_burst) else round(float(r.재현율_burst), 3)),
                 burst_p=(None if pd.isna(r.정밀도_burst) else round(float(r.정밀도_burst), 2)),
                 decay=round(float(r.재현율_decay), 3), decay_p=round(float(r.정밀도_decay), 2), organic=int(round(r.일반오탐_전체)),
                 tau_url=str(r.tau_url).split("/")[0]) for r in G.itertuples()]
    st = []
    if os.path.exists(p5):
        for r in pd.read_csv(p5).itertuples():
            st.append(dict(ratio=float(r.ratio), alert_all=int(round(r.ALERT_전체)), alert_support=round(float(r.ALERT_찬성만), 1)))
    return dict(rows=rows, stance=st, colors=dict(burst="#eb6834", decay="#2a78d6"))


def main():
    D = EH.build_data()
    D["sat"] = EH.sat_payload()
    D["duel"] = duel_payload()
    html = TEMPLATE.replace("/*PLOTLY*/", EH.plotly_js()).replace("/*DATA*/", json.dumps(D, ensure_ascii=False))
    out = os.path.join(HERE, "demo_story.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"demo_story.html 생성 ({len(html)/1e6:.1f} MB) · 9단계 한 화면 시연")


if __name__ == "__main__":
    main()
