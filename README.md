# 퐁네프 · 베른 예약 현황 자동 알림

매일 밤 **23:59(한국시간)** 에 대부도펜션시티 실시간예약 페이지에서 **퐁네프(파리동)·베른(스위스동)** 예약 상태를
**오늘부터 다음 달 말일까지** 확인하고, 달력 형태 현황표 이미지를 **카카오톡 '나와의 채팅'** 으로 보냅니다.

- 비용: 무료 (GitHub Actions 무료 사용량 안에서 동작)
- 컴퓨터가 꺼져 있어도 동작
- GitHub 예약 실행은 서버 사정으로 **5~30분 늦게** 올 수 있어요 (보통 0시 전후 도착)

---

## 처음 한 번만 하는 설정 (약 20분)

### 1단계. GitHub 저장소 만들기
1. https://github.com 가입/로그인
2. 오른쪽 위 **+ → New repository** → 이름 `pension-checker` → **Public** 선택 → Create
   (현황표 이미지를 카톡에 띄우려면 Public이어야 합니다. 원래 고객용 사이트에 공개된 정보라 문제없어요.)
3. 저장소 화면에서 **uploading an existing file** 클릭 → 이 폴더의 파일을 **전부(.github 폴더 포함)** 끌어다 놓고 Commit
   - `.github` 폴더가 안 올라가면: **Add file → Create new file** 에서 이름을 `.github/workflows/daily.yml` 로 쓰고 내용 붙여넣기 (kakao-setup.yml 도 동일)

### 2단계. GitHub 토큰(GH_PAT) 만들기 — 카카오 토큰 자동 갱신용
1. GitHub 오른쪽 위 프로필 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. Expiration: **No expiration** (또는 최대), Repository access: **Only select repositories → pension-checker**
3. Permissions → Repository permissions → **Secrets: Read and write**
4. Generate → 나온 토큰 복사

### 3단계. 카카오 개발자 앱 만들기
1. https://developers.kakao.com → 로그인 → **내 애플리케이션 → 애플리케이션 추가하기** (이름: 펜션알림)
2. **앱 키** 메뉴에서 **REST API 키** 복사
3. **카카오 로그인** 메뉴 → 활성화 **ON** → Redirect URI에 `https://localhost` 등록
4. **카카오 로그인 → 동의항목** → **카카오톡 메시지 전송** → 선택 동의로 설정
5. **플랫폼 → Web** → 사이트 도메인에 `https://raw.githubusercontent.com` 와 `https://github.com` 등록
6. (보안 메뉴에 **Client Secret** 이 '사용함'이면 그 값도 복사)

### 4단계. GitHub에 비밀값 넣기
저장소 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|---|---|
| `KAKAO_REST_KEY` | 3단계의 REST API 키 |
| `GH_PAT` | 2단계의 GitHub 토큰 |
| `KAKAO_CLIENT_SECRET` | (Client Secret 사용 중일 때만) |

### 5단계. 카카오톡 연결 (1회)
1. 브라우저 주소창에 아래 주소 입력 (`REST키` 부분을 내 키로 바꾸기)
   `https://kauth.kakao.com/oauth/authorize?client_id=REST키&redirect_uri=https://localhost&response_type=code&scope=talk_message`
2. 카카오 로그인 → 동의 → "사이트에 연결할 수 없음" 화면이 떠도 정상!
   주소창의 `code=` **뒤의 값 전체**를 복사
3. 저장소 → **Actions → 카카오톡 최초 연결 (1회만) → Run workflow** → code 칸에 붙여넣기 → Run
   (code는 10분 안에 써야 합니다. 실패하면 1번부터 다시)
4. 카톡 '나와의 채팅'에 "연결됐습니다 ✅" 메시지가 오면 성공

### 6단계. 바로 테스트
**Actions → 펜션 예약 현황 (매일 23:59) → Run workflow** → 1~3분 뒤 카톡으로 현황표 도착하면 끝!

---

## 문제가 생기면
- **카톡이 안 와요** → Actions 탭에서 빨간 X 실행을 눌러 오류 확인. 대부분 카카오 연결이 끊긴 경우라 5단계를 다시 하면 됩니다.
- **현황표에 '확인실패'가 보여요** → 그 시간에 펜션 사이트가 응답하지 않은 것. 다음 날 자동으로 다시 확인합니다.
- **사이트 구조가 바뀌어 전부 '미오픈'으로 나와요** → 위탁업체가 페이지를 개편한 경우라 `check.py` 수정이 필요합니다.
- 다른 객실도 보고 싶으면 `check.py` 의 `TARGETS` 줄에 `("객실명", "동이름앞부분", "동이름")` 추가.
