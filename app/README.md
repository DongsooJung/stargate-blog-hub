# 스타게이트 블로그 읽기 앱

운영 주소는 https://blog.stargateedu.co.kr/app/ 입니다. Android 앱의 시작 주소와 같은 경로에 앱 파일을 함께 배포합니다.

운영 소스는 이 저장소(DongsooJung/stargate-blog-hub)입니다. 기존 DongsooJung/stargate-blog의 읽기 앱을 복구했으며, 운영 수정은 이곳에서 진행합니다.

- 홈, 채널, 검색, 내 기록은 해시 경로를 사용합니다. Google Blog는 #/channels/blogger에서 읽습니다.
- 글 목록과 본문은 같은 디렉터리의 feed.json에서 읽습니다.
- python scripts/build_reader_feed.py로 글 목록을 갱신합니다. reader-feed.yml이 기존 앱과 같은 일정(매일 한국시간 03:15)으로 실행합니다.
- 기존 Pages 헬스체크가 앱 시작 주소와 필수 파일의 HTTP 200 응답을 함께 점검합니다.

별도 빌드 없이 이 디렉터리 전체를 GitHub Pages로 게시합니다.
