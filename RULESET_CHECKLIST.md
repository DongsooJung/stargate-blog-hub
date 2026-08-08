# GitHub Ruleset 적용 체크리스트

이 저장소의 운영 원본은 `main`입니다. 이 저장소에는 예약 워크플로가 생성 결과를 `main`에 직접 커밋하는 운영 구조가 있으므로, 일반 웹사이트 저장소와 동일한 PR 강제 규칙을 그대로 적용하면 자동발행이 중단됩니다.

## 자동화 사전 확인

다음 워크플로는 현재 `git push`로 결과물을 갱신합니다.

- `.github/workflows/notion-blog-sync.yml`
- `.github/workflows/notion-reading-sync.yml`
- `.github/workflows/허브_RSS_자동갱신.yml`

따라서 자동화를 PR 생성 방식 또는 별도 배포 브랜치 방식으로 전환하기 전까지는 **Require a pull request before merging을 활성화하지 않습니다.**

## 현재 권장 설정

1. **Settings → Rules → Rulesets → New branch ruleset**으로 이동합니다.
2. 이름을 `protect-main`, Enforcement status를 **Active**로 설정합니다.
3. Target branches에서 **Include default branch**를 선택합니다.
4. 다음 규칙을 켭니다.
   - Restrict deletions
   - Block force pushes
   - Require status checks to pass
5. 필수 상태 검사에 `CodeQL / JavaScript`를 추가합니다.
   - 이 검사는 먼저 한 번 성공해야 선택 목록에 나타날 수 있습니다.
   - 초기에는 **Require branches to be up to date**를 끄고 운영 마찰을 줄입니다.
6. **Require a pull request before merging은 현재 보류**합니다.
7. 자동화가 PR 또는 배포 브랜치 방식으로 전환된 후 다음을 추가합니다.
   - Require a pull request before merging
   - Dismiss stale pull request approvals when new commits are pushed
   - Require conversation resolution before merging
8. 테스트 브랜치에서 CodeQL 통과 여부와 예약 워크플로의 `main` 갱신 성공 여부를 각각 확인합니다.

## 적용 완료 기준

- [ ] `protect-main` ruleset이 Active
- [ ] 삭제와 force-push 차단
- [ ] `CodeQL / JavaScript` 상태 검사 필수
- [ ] 예약 워크플로 3종의 자동 갱신 성공
- [ ] 자동화 PR/배포 브랜치 전환 전까지 PR 강제 규칙 보류
- [ ] 자동화 전환 후 PR 강제·대화 해결 규칙 활성화

## 다음 개선 작업

- [ ] 예약 워크플로 결과물을 별도 자동화 브랜치 또는 artifact로 분리
- [ ] 자동 생성 PR의 중복 방지와 자동 병합 조건 정의
- [ ] 전환 완료 후 직접 `main` 푸시 차단 검증

참고: [GitHub Rulesets 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
