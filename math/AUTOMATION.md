# STARGATE MATH Daily 운영 문서

## 목적

`stargateedu.co.kr/research/math/archive/problems.json`을 단일 원천 데이터로 사용해 `blog.stargateedu.co.kr/math/`에 한 번에 한 문제씩 발행한다.

## 파이프라인

1. 연구 저장소: `research/math/archive/problems.json`
2. 발행기: `scripts/publish_math_problem.py`
3. 발행 상태: `math/publish-state.json`
4. 블로그 피드: `math/posts.json`
5. 개별 SEO 페이지: `math/problems/<problem-id>/index.html`
6. 네이버용 원고 큐: `math/naver-queue/<problem-id>.json`

## 현재 운영 상태

- 자동 스케줄: 매일 KST 10:10
- 기본 상태: **DRY RUN / 자동발행 OFF**
- 한 번 실행 시 최대 1문제만 발행
- 중복 방지: `publish-state.json`의 `published` 배열 사용
- 공개 원문 복제 금지: 모든 성대경시형·생각하는황소형 문항은 교육용 재구성 문제로만 운영

## 수동 발행

GitHub Actions → `Math Daily 하루 한 문제` → `Run workflow` → `mode=publish`.

수동 실행도 정확히 1문제만 처리한다. 다음 queued 문항을 선택하고 페이지/피드/상태/네이버용 원고를 함께 생성한다.

## 자동발행 활성화

Repository variable `MATH_AUTO_PUBLISH_ENABLED`를 `true`로 설정하면 매일 KST 10:10 스케줄에서 1문제를 발행한다.

`false`, 미설정 또는 다른 값이면 스케줄은 dry-run만 수행한다.

## 권장 활성화 순서

초기 3건은 수동 `publish`로 제목·수식·모바일 표시를 확인한다. 이상이 없으면 `MATH_AUTO_PUBLISH_ENABLED=true`로 전환한다.

## 네이버 블로그

현재 공식 Naver Developers 문서 기준으로 과거 블로그 글쓰기 API를 신규 자동화 대상으로 사용하지 않는다. 대신 각 발행 시 `math/naver-queue/<id>.json`에 제목, 본문 텍스트, 태그를 함께 생성해 수동 게시 또는 향후 브라우저 기반 승인형 게시에 사용한다.

## 확장 규칙

문제를 늘릴 때는 중앙 `problems.json`에 새 항목을 추가하고 `blog_status`를 `queued`로 설정한다. 발행기 코드는 수정할 필요가 없다.
