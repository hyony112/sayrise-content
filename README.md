# sayrise-content — 말해야 꺼지는 모닝콜 확언 목록

이 폴더는 확언 목록만 담는 **공개 GitHub 저장소**의 템플릿이에요. 앱 소스와 분리해 두고 GitHub Pages로 `affirmations.json`을 공개해요.

```
Google 시트 (편집) → Actions "확언 배포" (검사·변환) → docs/affirmations.json (GitHub Pages) → 앱
                                                                    받기 실패·검사 실패 시 ↘ 앱 내장 목록
```

## 처음 한 번 설정

1. **저장소 만들기**: 이 폴더 내용으로 공개 저장소 `sayrise-content`를 만들어요.
2. **GitHub Pages**: Settings → Pages → Source: *Deploy from a branch*, Branch: `main` / `/docs`.
   주소는 `https://<GitHub 아이디>.github.io/sayrise-content/affirmations.json`이 돼요.
3. **Google 시트**: `affirmations.csv`를 새 시트로 가져와요(파일 → 가져오기).
   - 머리글: `id`, `카테고리`, `확언`, `사용` (그대로 두세요)
   - `사용` 열에 드롭다운(Y/N)을 걸어 두면 편해요.
   - 편의용 열을 더 만들어도 돼요(예: `어절 수` = `=IF(C2="","",COUNTA(SPLIT(C2," ")))`). 모르는 열은 무시해요.
4. **시트 게시**: 파일 → 공유 → 웹에 게시 → 해당 시트, *쉼표로 구분된 값(.csv)* → 링크 복사.
5. **변수 등록**: 저장소 Settings → Secrets and variables → Actions → Variables → `SHEET_CSV_URL`에 4번 링크.
6. **앱 연결**: 앱 `SayRise-Info.plist`의 `AffirmationsURL`에 2번 주소를 넣어요.

## 확언을 고칠 때

1. 시트에서 고쳐요.
2. 저장소 → Actions → **확언 배포** → Run workflow.
3. 결과 요약에 `✓ … version N`이 나오면 배포 끝. 앱은 다음에 켜질 때 받아가요.
   검사에 실패하면 어느 행이 왜 틀렸는지 나오고, 아무것도 배포하지 않아요.

## 규칙 (기획서 5장, 앱과 스크립트가 같은 규칙으로 검사)

- 6~12어절, 한글과 띄어쓰기 한 칸만 (숫자·영어·문장부호 금지)
- 한 글자 어절은 2개까지
- `id`는 소문자·숫자·하이픈. **한 번 쓴 id는 바꾸거나 지우지 않아요.** 빼고 싶으면 `사용`을 N으로.
- 사용 중인 확언이 10개 이상이어야 해요.
- 새 문장은 실기기에서 직접 읽어 보고 넣어요.

## 출시 전: 앱 내장 목록 맞추기

앱에는 배포된 목록과 **같은 파일**이 기본값으로 들어 있어야 해요(오프라인 대비, 버전 번호도 같게). 출시 빌드 전에 앱 저장소에서:

```bash
curl -fsSL "https://<GitHub 아이디>.github.io/sayrise-content/affirmations.json" -o SayRise/affirmations.json
python3 content/scripts/affirmations.py check SayRise/affirmations.json
```
