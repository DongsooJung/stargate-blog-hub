# 스타게이트 블로그 읽기 앱

운영 주소는 https://blog.stargateedu.co.kr/app/ 입니다. Android 앱의 시작 주소와 같은 경로에 앱 파일을 함께 배포합니다.

운영 소스는 이 저장소(DongsooJung/stargate-blog-hub)입니다. 기존 DongsooJung/stargate-blog의 읽기 앱을 복구했으며, 운영 수정은 이곳에서 진행합니다.

- 홈, 채널, 검색, 내 기록은 해시 경로를 사용합니다. Google Blog는 #/channels/blogger에서 읽습니다.
- 글 목록과 본문은 같은 디렉터리의 feed.json에서 읽습니다.
- python scripts/build_reader_feed.py로 글 목록을 갱신합니다. reader-feed.yml이 기존 앱과 같은 일정(매일 한국시간 03:15)으로 실행합니다.
- 기존 Pages 헬스체크가 앱 시작 주소와 필수 파일의 HTTP 200 응답을 함께 점검합니다.

별도 빌드 없이 이 디렉터리 전체를 GitHub Pages로 게시합니다.

## Android 빌드 소스 (2026-10-31 이관)

- Play에 올라간 1.0.0은 예전 저장소의 Gradle 프로젝트로 만들었습니다. 그 프로젝트를 `android/gradle/`로 옮겼고, 다음 버전은 1.0.1(versionCode 2)입니다.
- Bubblewrap 설정 `android/twa-manifest.json`도 시작 주소를 `/app/`으로 맞췄습니다. 두 방식 중 Play에 등록된 업로드 키로 서명하는 쪽 하나만 사용합니다.
- Play 등록 문구와 스크린샷은 `store/`에 있습니다.
- 예전 저장소 DongsooJung/stargate-blog는 보관(archive) 처리했습니다.
