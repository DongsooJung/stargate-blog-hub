# stargate-blog-hub

[`blog.stargate11.com`](https://blog.stargate11.com/) — 정동수의 멀티 블로그/SNS 통합 랜딩.

매일 **KST 03:00** GitHub Actions 가 4개 채널(네이버 개인·법인 / 티스토리 / Medium) RSS 를
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
                  ├─── Medium RSS (예정) ──────┤
                  └─── (LinkedIn 확장 예정) ───┘
```

## 디렉터리 구성

```
stargate-blog-hub/
├── CNAME                               # blog.stargate11.com
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
3. `build_hub_index.py` 가 4개 RSS 를 병렬 수집(채널당 최신 5개)
4. 전체 목록을 날짜 역순으로 정렬 후 상위 20개를 템플릿에 주입
5. 생성된 `index.html` 가 기존 파일과 diff 될 때만 자동 커밋(봇 계정: `stargate-hub-bot`)
6. GitHub Pages 가 즉시 배포 → CDN 전파 후 `blog.stargate11.com` 노출

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
  -f "cname=blog.stargate11.com" -F "https_enforced=true"

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
| 수시 | Medium/LinkedIn 피드 추가 | `build_hub_index.py` `FEEDS` 수정 |
| 월 1회 | 채널 카드 문구 업데이트 | `templates/허브_템플릿.html` 수동 편집 |

## 확장 로드맵

1. **Medium 실계정 개설** (`@stargate-en`) → FEEDS 주석 해제
2. **LinkedIn Company Page API** 연동 (OAuth2 + GitHub Secrets)
3. **GA4 + GTM** 통합 스크립트 `<head>` 삽입
4. **Jekyll 확장** — `_config.yml` + `_posts/YYYY-MM-DD-title.md` 로 본 사이트에서 글 발행
5. **Cloudflare Pages 이관** — Edge 함수 + 글로벌 CDN 성능 개선

## 검증 명령

```bash
dig +short blog.stargate11.com                    # → dongsoojung.github.io.
curl -sI https://blog.stargate11.com/ | head -5   # → HTTP/2 200
curl -s  https://blog.stargate11.com/ | grep -c "latest-item"  # → 15~20
```

## 라이선스 · 운영 주체

© 2026 Stargate Corporation · 주식회사 별의문.
콘텐츠 라이선스는 각 원본 블로그 약관을 따르며, 본 허브는 링크 인덱스만 보관합니다.
