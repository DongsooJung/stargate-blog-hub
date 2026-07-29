# stargate-blog-hub

[`blog.stargateedu.co.kr`](https://blog.stargateedu.co.kr/) — 정동수의 멀티 블로그/SNS 통합 랜딩.

매일 **KST 03:00** GitHub Actions 가 4개 채널(네이버 개인·법인 / 티스토리 / YouTube 우주인) RSS 를
수집해 상단 "🔥 최신 포스팅" 섹션을 자동 갱신합니다.

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
                  ┌─── 네이버 개인 RSS ─────────┤
                  ├─── 네이버 법인 RSS ─────────┤
  매일 03:00 KST ─┼─── 티스토리 RSS ───────────┼── feedparser
                  ├─── YouTube 우주인 RSS ─────┤
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
│       ├── 허브_RSS_자동갱신.yml        # 매시 정각 cron
│       └── Pages_헬스체크.yml           # 매주 월 KST 09:30 cron
├── posts.json                          # 자동 생성 · 새로고침 버튼의 데이터 소스
├── scripts/
│   ├── build_hub_index.py              # 메인 빌더
│   └── requirements.txt
└── templates/
    └── 허브_템플릿.html                 # Jinja2 템플릿
```

## 동작 원리

1. `허브_RSS_자동갱신.yml` 가 매시 정각 또는 수동 `workflow_dispatch` 로 트리거
2. Ubuntu 러너에서 Python 3.12 + `feedparser` + `Jinja2` 설치
3. `build_hub_index.py` 가 4개 RSS 를 수집(채널당 최신 5개)
4. 전체 목록을 날짜 역순으로 정렬 후 상위 20개를 템플릿에 주입
5. **목록이 직전 빌드와 같으면 아무 파일도 쓰지 않고 종료** — 갱신 시각이
   "마지막으로 글 목록이 실제로 바뀐 시각"을 가리키고, 빈 커밋도 생기지 않습니다
6. 변경이 있으면 `index.html` + `posts.json` 을 함께 갱신하고 자동 커밋(봇: `stargate-hub-bot`)
7. GitHub Pages 가 즉시 배포 → CDN 전파 후 `blog.stargateedu.co.kr` 노출

## 🔄 새로고침 버튼

"🔥 최신 포스팅" 헤더의 **새로고침** 버튼은 `posts.json` 을 `cache: no-store` +
쿼리스트링 캐시버스팅으로 다시 받아 목록을 그 자리에서 다시 그립니다.

- **CDN 캐시 우회** — 페이지 HTML 이 캐시돼 옛 글이 보여도 버튼 한 번이면 최신 목록으로 교체
- **새 글 표시** — 화면에 없던 글에는 초록색 `NEW` 배지와 테두리 강조
- **상태 안내** — `최신 상태 · HH:MM 확인` / `새 글 N개 · HH:MM 확인` / 실패 메시지
- **자동 동기화** — 페이지 진입 시 1회, 그리고 다른 탭에 다녀와 돌아올 때마다 조용히 갱신
- 실패해도 화면에 떠 있던 목록은 그대로 유지됩니다

> 버튼은 **직전 자동 갱신 결과**를 즉시 반영합니다. 브라우저에서 네이버·티스토리 RSS 를
> 직접 부르는 것은 CORS 로 차단되므로, 실제 수집은 매시 정각 Actions 가 담당합니다.
> 더 빠른 반영이 필요하면 Actions 에서 `허브 RSS 자동갱신` 을 수동 실행한 뒤 버튼을 누르세요.

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

출력 로그는 `[INFO] 네이버 개인: 5개 수집` 형태로 표시되며,
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
