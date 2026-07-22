# Notion 독후감 즉시 발행 웹훅

## Vercel 환경 변수

- `GITHUB_CONTENTS_TOKEN`: `DongsooJung/stargate-blog-hub` 한 저장소에만 Contents read/write 권한을 가진 Fine-grained GitHub PAT
- `NOTION_WEBHOOK_KEY`: 임의의 긴 비밀 문자열
- `GITHUB_REPOSITORY`: `DongsooJung/stargate-blog-hub` (선택)
- `GITHUB_BRANCH`: `main` (선택)

## Notion 자동화

대상 DB: `📖 독서 LOG & 독후감`

1. `⚡` → `New automation`
2. Trigger: `웹공개` property edited
3. Action: `Send webhook`
4. URL: 배포된 Vercel URL의 `/api/notion-reading-webhook`
5. Custom header: `X-Stargate-Webhook-Key` = Vercel의 `NOTION_WEBHOOK_KEY`와 동일한 값
6. 아래 속성을 모두 payload에 포함
   - 도서명, 저자, 대분류, 평점, 페이지수, 완독일
   - 한줄평, 인용문, 독후감본문, 추천대상, 핵심키워드
   - 독서상태, 웹공개

`웹공개=true`이고 `독서상태`가 `완독` 또는 `재독`이면 발행합니다. 체크를 해제하면 기존 공개 글을 제거합니다.
