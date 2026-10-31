# 공개 게시 준비

개발자 계정은 새로 만들지 않습니다. `kr.co.stargateedu.twa` 를 올린 기존 Play 계정에 앱을 추가합니다.

- 개발자 표시 이름: STARGATE
- 공개 메일: ceo@stargateedu.co.kr
- 법인명: 주식회사 별의문
- 개인정보처리방침: https://stargateedu.co.kr/privacy.html (2026-10-15)
- 패키지: kr.co.stargateedu.blog
- 시작 주소: https://blog.stargateedu.co.kr/app/
- 미리보기: (예전 저장소 stargate-blog 보관 처리로 중단, 운영 주소에서 바로 확인)

콘솔에 붙여 넣을 문구, 데이터 안전 답, 전체이용가 답은 `store/play-listing.md`에 있습니다.

## 화면

갤럭시 폴드7 접힘은 412×960, 펼침은 750×832 또는 984×1092입니다. 접힘에서는 글이 한 줄이고, 750px 이상에서는 두 칸, 900px 이상이면서 높이가 700px 이상이면 목록과 본문이 나란히 있습니다.

참고 캡처:

- `store/screenshots/04-fold7-cover.png`
- `store/screenshots/05-fold7-open-home.png`
- `store/screenshots/06-fold7-open-read.png`

Play에 올리는 전화 스크린샷 3장은 1080×1920이고 `01`부터 `03`입니다.

## 콘솔에서 이어서 할 일

1. 기존 개발자 계정에서 앱을 만듭니다. 패키지 이름은 `kr.co.stargateedu.blog`입니다.
2. `android/`로 App Bundle을 만듭니다. 이 환경에는 Android SDK가 없어 여기서는 만들지 못했습니다. 활동은 크기 변경을 허용합니다.
3. Play 앱 서명 인증서의 SHA-256을 `.well-known/assetlinks.json`에 넣습니다. 지금은 빈 배열입니다. `kr.co.stargateedu.twa`의 지문은 그대로 둡니다.
4. 그 자산 링크를 `blog.stargateedu.co.kr` 루트에 둡니다. 이 계정의 토큰으로는 `stargate-blog-hub`에 푸시하지 못합니다.
5. `app/`과 `feed.json`을 허브에 넣어 `https://blog.stargateedu.co.kr/app/`에서 열리게 합니다. 방문 수 실시간 조회는 그 출처만 허용합니다.
6. 스토어 등록 정보를 `store/play-listing.md`대로 채우고 내부 테스트에 올립니다. 프로덕션은 주소 확인이 끝난 뒤입니다.
