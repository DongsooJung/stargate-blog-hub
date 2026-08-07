# GitHub Ruleset 적용 체크리스트

이 저장소의 운영 원본은 `main`입니다. 아래 설정은 자동화 계정과 사람의 직접 푸시로 운영 원본이 덮어써지는 일을 방지하기 위한 권장값입니다.

## 적용 경로

1. **Settings → Rules → Rulesets → New branch ruleset**으로 이동합니다.
2. 이름을 `protect-main`, Enforcement status를 **Active**로 설정합니다.
3. Target branches에서 **Include default branch**를 선택합니다.
4. 다음 규칙을 켭니다.
   - Restrict deletions
   - Block force pushes
   - Require a pull request before merging
   - Dismiss stale pull request approvals when new commits are pushed
   - Require conversation resolution before merging
   - Require status checks to pass
5. 필수 상태 검사에 `CodeQL / JavaScript`를 추가합니다.
   - 이 검사는 먼저 한 번 성공해야 선택 목록에 나타날 수 있습니다.
   - 초기에는 **Require branches to be up to date**를 끄고 운영 마찰을 줄입니다.
6. 현재 단독 운영이면 Required approvals는 **0**으로 둡니다. 별도 리뷰 권한자가 생기면 **1**로 올립니다.
7. Bypass list는 비워 두는 것을 원칙으로 합니다. 긴급 복구용 우회가 필요하면 저장소 소유자만 제한적으로 지정합니다.
8. 저장 후 테스트 브랜치에서 PR을 만들고, 직접 `main` 푸시가 차단되며 CodeQL 통과 후 병합되는지 확인합니다.

## 적용 완료 기준

- [ ] `protect-main` ruleset이 Active
- [ ] 삭제와 force-push 차단
- [ ] 변경은 PR을 통해서만 병합
- [ ] `CodeQL / JavaScript` 상태 검사 필수
- [ ] 직접 `main` 푸시 차단 검증
- [ ] 공동 리뷰어 확보 시 승인 1명으로 상향

참고: [GitHub Rulesets 문서](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
