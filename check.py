"""퐁네프(파리동) · 베른(스위스동) 예약 현황을 확인해서 이미지로 만들고 카카오톡 '나에게 보내기'로 전송."""
import calendar, datetime as dt, json, os, subprocess, sys, time
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
BASE = "http://pensioncity.kr/bbs/board.php"
TARGETS = [("퐁네프", "파리", "파리동"), ("베른", "스위스", "스위스동")]  # (객실명, rm_cate, 동 이름)
STATUS = {"완료": "bk", "예약하기": "av", "결제중": "pd", "대기": "pd"}
LABEL = {"bk": "예약", "av": "빈방", "pd": "결제중", "na": "미오픈", "er": "확인실패"}
HEAD = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0 Safari/537.36"}

def fetch_day(cate, day):
    params = {"bo_table": "pensionstatus", "mode": "step1", "rm_cate": cate, "rmType": "A", "sch_day": day.isoformat()}
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, headers=HEAD, timeout=20)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            rooms = {}
            for tr in soup.find_all("tr"):
                cells = [td.get_text("\n", strip=True).split("\n")[0] if td.get_text(strip=True) else "" for td in tr.find_all("td")]
                k = next((i for i, c in enumerate(cells) if "평형" in c), None)
                if k is None or k == 0:
                    continue
                st = next((c for c in reversed(cells) if c in STATUS), None)
                rooms[cells[k - 1].strip()] = st
            return rooms
        except Exception as e:
            print("retry", cate, day, e, file=sys.stderr); time.sleep(3)
    return None

def collect(start, end):
    data = {}
    d = start
    while d <= end:
        row = []
        for room, cate, _ in TARGETS:
            rooms = fetch_day(cate, d)
            if rooms is None: row.append("er")
            elif room not in rooms: row.append("na")
            else: row.append(STATUS.get(rooms[room], "er"))
            time.sleep(0.3)
        data[d] = row
        d += dt.timedelta(days=1)
    return data

def month_html(y, m, data):
    h = f'<div class="mon"><h2>{y}년 {m}월</h2><table><tr>' + "".join(
        f'<th class="{"sun" if i==0 else "sat" if i==6 else ""}">{w}</th>' for i, w in enumerate("일월화수목금토")) + "</tr>"
    for wk in calendar.Calendar(6).monthdatescalendar(y, m):
        h += "<tr>"
        for i, d in enumerate(wk):
            if d.month != m: h += '<td class="out"></td>'; continue
            cls = "sun" if i == 0 else "sat" if i == 6 else ""
            if d in data:
                inner = "".join(f'<div class="chip {s}"><b>{TARGETS[j][0]}</b>{LABEL[s]}</div>' for j, s in enumerate(data[d]))
            else:
                inner = '<div class="past">지난 날짜</div>'
            h += f'<td><div class="dn {cls}">{d.day}</div>{inner}</td>'
        h += "</tr>"
    return h + "</table></div>"

def summary(data, months):
    rows, text = "", []
    for y, m in months:
        ds = [d for d in data if (d.year, d.month) == (y, m)]
        for j, (room, _, dong) in enumerate(TARGETS):
            bk = [d for d in ds if data[d][j] == "bk"]; pd = [d for d in ds if data[d][j] == "pd"]
            f = lambda L: ", ".join(f"{d.month}/{d.day}" for d in L) or "-"
            rows += f'<tr><td>{m}월</td><td><b>{room} ({dong})</b></td><td class="n">{len(bk)}박</td><td class="n">{len(pd)}박</td><td>{f(bk)}</td><td>{f(pd)}</td></tr>'
            text.append(f"[{m}월] {room} 예약 {len(bk)}박" + (f" ({f(bk)})" if bk else "") + (f" / 결제중 {f(pd)}" if pd else ""))
    return rows, text

CSS = open(os.path.join(os.path.dirname(__file__), "style.css"), encoding="utf-8").read()

def render(data, now, months):
    rows, text = summary(data, months)
    errs = sum(s == "er" for v in data.values() for s in v)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<h1>퐁네프 · 베른 예약 현황</h1>
<div class="sub">조회 시각 {now:%Y년 %m월 %d일 %H:%M} (한국시간) · 출처: 대부도펜션시티 실시간예약 페이지(고객용 화면)</div>
<table class="sum"><tr><th>월</th><th>객실</th><th>예약완료</th><th>결제중</th><th>예약완료 날짜</th><th>결제중 날짜</th></tr>{rows}</table>
<div class="leg"><span class="bk">예약완료</span><span class="pd">결제중</span><span class="av">빈방</span><span class="na">미오픈</span></div>
<div class="mons">{"".join(month_html(y, m, data) for y, m in months)}</div>
<div class="note">* 날짜는 입실일(1박) 기준. ‘미오픈’ = 예약 페이지에 객실이 표시되지 않은 날(판매중지·관리 차단 추정).{f" ※ {errs}건 조회 실패" if errs else ""}</div>
</body></html>'''
    os.makedirs("out", exist_ok=True)
    open("out/report.html", "w", encoding="utf-8").write(html)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1164, "height": 800}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath("out/report.html")); pg.wait_for_timeout(500)
        pg.screenshot(path="out/report.png", full_page=True); b.close()
    return text, errs

# ---------------- 카카오톡 ----------------
def kakao_token():
    r = requests.post("https://kauth.kakao.com/oauth/token", data={
        "grant_type": "refresh_token", "client_id": os.environ["KAKAO_REST_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
        **({"client_secret": os.environ["KAKAO_CLIENT_SECRET"]} if os.environ.get("KAKAO_CLIENT_SECRET") else {})}, timeout=20)
    r.raise_for_status(); j = r.json()
    if j.get("refresh_token"):  # 리프레시 토큰이 새로 발급되면 GitHub Secret 자동 갱신
        subprocess.run(["gh", "secret", "set", "KAKAO_REFRESH_TOKEN", "--body", j["refresh_token"]], check=False)
        print("refresh token renewed")
    return j["access_token"]

def kakao_send(text_lines, image_url, page_url):
    tok = kakao_token()
    tpl = {"object_type": "feed", "content": {
        "title": "퐁네프·베른 예약 현황", "description": "\n".join(text_lines)[:200],
        "image_url": image_url, "image_width": 800, "image_height": 600,
        "link": {"web_url": page_url, "mobile_web_url": page_url}},
        "buttons": [{"title": "현황표 크게 보기", "link": {"web_url": page_url, "mobile_web_url": page_url}}]}
    r = requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send",
                      headers={"Authorization": f"Bearer {tok}"}, data={"template_object": json.dumps(tpl, ensure_ascii=False)}, timeout=20)
    print("kakao:", r.status_code, r.text); r.raise_for_status()

if __name__ == "__main__":
    now = dt.datetime.now(KST)
    start = now.date()
    nm = (start.replace(day=28) + dt.timedelta(days=10))           # 다음 달
    end = nm.replace(day=calendar.monthrange(nm.year, nm.month)[1])  # 다음 달 말일까지
    months = [(start.year, start.month), (nm.year, nm.month)]
    if "--demo" in sys.argv:
        data = {start + dt.timedelta(days=i): [["av", "bk", "pd"][i % 3], ["bk", "av", "na"][i % 3]] for i in range((end - start).days + 1)}
    else:
        data = collect(start, end)
    text, errs = render(data, now, months)
    print("\n".join(text))
    open("out/summary.txt", "w", encoding="utf-8").write("\n".join(text))
    if os.environ.get("KAKAO_REST_KEY") and "--no-send" not in sys.argv:
        img = os.environ["IMAGE_URL"] + f"?t={int(time.time())}"
        kakao_send(text, img, img)
