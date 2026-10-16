# stargate-blog-hub

## 블로그 방문자 수

메인 배너의 ‘오늘 · 누적’은 기존 Firebase 프로젝트의 Firestore에 별도로 저장합니다.
같은 브라우저는 한국시간 기준 하루 1회 집계하며, 누적은 일별 방문 합계입니다.
`assets/blog-visitors.js`가 기존 Cloudflare Worker의 `/api/blog-visitors`를 호출합니다.
서버가 중복을 확인하고 집계하며 서비스 계정 키는 브라우저에 전달하지 않습니다.
RSS 자동 갱신 뒤에도 유지되도록 `templates/허브_템플릿.html`과 `index.html`에 함께 적용합니다.
집계는 연결 시점부터 시작하며, 메인 포털 방문자 수와 합산하지 않습니다.

[`blog.stargateedu.co.kr`](https://blog.stargateedu.co.kr/) — 정동수의 멀티 블로그/SNS 통합 랜딩.

매일 **KST 03:00** GitHub Actions가 5개 채널(부동산·경제 / 수학·AI / 정치·데이터 / Google Blog / YouTube 우주인) RSS를
수집해 상단 ‘새로 도착한 글’ 섹션을 자동 갱신합니다.

## 1·2차 홈 개편

- 한글 대표 제목, 핵심 메뉴 4개와 더보기, 최신 글 → 주제 → 8개 채널 → Notion 아카이브 순서.
- 최신 글은 처음 6개, 더보기마다 6개씩 최대 20개. JavaScript가 없으면 모든 글을 표시합니다.
- Blogger: `https://jds0688.blogspot.com/`, RSS: `/feeds/posts/default?alt=rss`.
- HTML 엔티티와 제목 앞 마크다운 헤딩을 정리하고, 실제 HTML은 템플릿에서 이스케이프합니다.
- 원문을 식별하는 쿼리는 보존하며 추적 매개변수·모바일 주소 차이·같은 YouTube 영상의 중복을 제거합니다.
- 발행 시각을 보존해 한국시간으로 표시하고 시각순으로 정렬합니다.
- PC 채널 4열, 태블릿 2열, 모바일은 간결한 목록. 홈페이지 전용 스타일은 `assets/hub-home.css`입니다.
- 전체 RSS 수집 실패 시 기존 `index.html`을 보존합니다. 채널별 이전 데이터 복구는 별도 후속 과제입니다.

검증: `python -m unittest discover -s tests -p 'test_hub_builder.py' -v`, `node --check latest-refresh.js`.

메인 페이지 하단의 **"최신 글 · Notion Blog"** 섹션과 `/posts/` 페이지는 `posts/posts.json`을 함께 읽습니다.
노션 동기화 작업이 이 파일을 갱신하면 두 화면에 새 글과 본문이 동시에 반영됩니다.

---

## 아키텍처

```
     ┌─────────────────────────────────────────────────────────┐
     │                GitHub Pages (public repo)                │
     │                                                          │
     │   index.html  ◀── Jinja2 render ── templates/허브_템플릿.html
     │        ▲                                │                │
     │        │                                │                │
     │        └── Actions commit ──────────────┤                │
     │                                         │                │
     └─────────────────────────────────────────┼────────────────┘
                                               │
                  ┌─── 부동산·경제 RSS ────────┤
                  ├─── 수학·AI RSS ────────────┤
  매일 03:00 KST ─┼─── 정치·데이터 RSS ────────┼── feedparser
                  ├─── YouTube 우주인 RSS ─────┤
                  ├─── Google Blog RSS ───────┤
                  └─── (LinkedIn 확장 예정) ───┘
```

## 디렉터리 구성

```
stargate-blog-hub/
├── CNAME                               # blog.stargateedu.co.kr
├── index.html                          # 자동 생성 (커밋 대상)
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       ├── 허브_RSS_자동갱신.yml        # 매일 KST 03:00 cron
│       └── Pages_헬스체크.yml           # 매주 월 KST 09:30 cron
├── scripts/
│   ├── build_hub_index.py              # 메인 빌더
│   └── requirements.txt
└── templates/
    └── 허브_템플릿.html                 # Jinja2 템플릿
```

## 동작 원리

1. `허브_RSS_자동갱신.yml` 가 매일 KST 03:00 또는 수동 `workflow_dispatch` 로 트리거
2. Ubuntu 러너에서 Python 3.12 + `feedparser` + `Jinja2` 설치
3. `build_hub_index.py`가 5개 RSS를 수집(채널당 중복 없는 최신 5개)
4. 전체 목록의 중복을 제거하고 발행 시각 역순으로 정렬 후 상위 20개를 템플릿에 주입
5. 생성된 `index.html` 가 기존 파일과 diff 될 때만 자동 커밋(봇 계정: `stargate-hub-bot`)
6. GitHub Pages 가 즉시 배포 → CDN 전파 후 `blog.stargateedu.co.kr` 노출

## 배포 (최초 1회)

### 방법 A: 자동 배포 스크립트 (권장)

Windows PowerShell 에서 `260420_멀티블로그_통합관리/scripts/GitHub_허브_배포.ps1` 실행.
`gh` CLI 가 설치·인증되어 있어야 합니다.

```powershell
cd "C:\Users\DONGSOO_PC\Desktop\Cowork(260323)\260420_홈페이지통합관리\shop_blog_연결계획\stargate-blog-hub"
powershell -ExecutionPolicy Bypass -File "..\..\..\260420_멀티블로그_통합관리\scripts\GitHub_허브_배포.ps1"
```

### 방법 B: 수동 배포

```bash
cd stargate-blog-hub
git init -b main
git add .
git commit -m "feat: 허브 자동 갱신 파이프라인 초기 배포"

gh repo create DongsooJung/stargate-blog-hub --public --source=. --remote=origin --push

# Pages 설정
gh api -X POST "repos/DongsooJung/stargate-blog-hub/pages" \
  -f "source[branch]=main" -f "source[path]=/"
gh api -X PUT "repos/DongsooJung/stargate-blog-hub/pages" \
  -f "cname=blog.stargateedu.co.kr" -F "https_enforced=true"

# Actions 최초 실행
gh workflow run "허브_RSS_자동갱신.yml"
```

이후 Cafe24 DNS 에 CNAME 레코드(`blog` → `dongsoojung.github.io`, TTL 600) 를 추가합니다.

## 로컬 테스트

```bash
cd scripts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python build_hub_index.py
# → ../index.html 생성 (최신 20개 포스팅 반영)
```

출력 로그는 `[INFO] 부동산·경제: 5개 수집` 형태로 표시되며,
실패 채널은 `::warning::` 으로 GitHub Actions UI 에서도 하이라이트됩니다.

## 운영

| 주기 | 작업 | 담당 |
|------|------|------|
| 매일 03:00 KST | RSS 수집 + 커밋 | Actions (자동) |
| 매주 월 09:30 KST | 헬스체크 + Issue 알림 | Actions (자동) |
| 수시 | YouTube 채널 변경·외부 피드 추가 | `build_hub_index.py` `FEEDS` 수정 |
| 월 1회 | 채널 카드 문구 업데이트 | `templates/허브_템플릿.html` 수동 편집 |

## 확장 로드맵

1. **YouTube Data API 연동** → 라이브 상태·재생목록 메타데이터 확장
2. **LinkedIn Company Page API** 연동 (OAuth2 + GitHub Secrets)
3. **GA4 + GTM** 통합 스크립트 `<head>` 삽입
4. **Jekyll 확장** — `_config.yml` + `_posts/YYYY-MM-DD-title.md` 로 본 사이트에서 글 발행
5. **Cloudflare Pages 이관** — Edge 함수 + 글로벌 CDN 성능 개선

## 검증 명령

```bash
dig +short blog.stargateedu.co.kr                    # → dongsoojung.github.io.
curl -sI https://blog.stargateedu.co.kr/ | head -5   # → HTTP/2 200
curl -s  https://blog.stargateedu.co.kr/ | grep -c "latest-item"  # → 15~20
```

## 라이선스 · 운영 주체

© 2026 Stargate Corporation · 주식회사 별의문.
콘텐츠 라이선스는 각 원본 블로그 약관을 따르며, 본 허브는 링크 인덱스만 보관합니다.
