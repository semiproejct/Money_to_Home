# 첫 PR 연습

| 항목 | 내용 |
| --- | --- |
| 대상 | Git으로 올려 본 적이 없는 팀원 |
| 걸리는 시간 | 10분 |
| 목표 | 자기 브랜치를 만들어 파일 하나를 올리고 PR을 연다. 이것이 되면 올리기 권한까지 확인된 것이다. |
| 먼저 끝낼 것 | `docs/setup_guide.md`의 1 ~ 5단계 |

앞으로 하는 모든 작업이 이 순서를 따른다. **브랜치 만들기 → 고치기 → 담기 → 기록하기 → 올리기 → PR 열기.**

## 먼저 알아 둘 말

| 말 | 뜻 |
| --- | --- |
| 브랜치 | 작업 갈래. 내 작업이 남의 작업과 섞이지 않게 따로 만든다. |
| 커밋 | 바뀐 내용을 기록으로 남기는 것 |
| 푸시 (push) | 내 PC의 기록을 GitHub에 올리는 것 |
| PR (Pull Request) | "내 브랜치의 내용을 합쳐 주세요"라고 요청하는 것 |
| 머지 (merge) | PR을 받아들여 합치는 것. 팀장이 한다. |

## 순서

VS Code에서 `C:\projects\Money_to_Home` 폴더를 열고, **터미널 > 새 터미널**을 누른다. 아래를 한 줄씩 적고 Enter를 누른다.

`이름` 자리에는 자기 영문 이름을 적는다. 예: `chaeeun`, `moksan`, `sehwan`, `haewon`

### 1. 자기 브랜치를 만든다

```
git checkout -b chore/setup-이름
```

`Switched to a new branch`가 나오면 맞다.

### 2. 파일을 하나 만든다

1. VS Code 왼쪽에서 `docs` 폴더를 펼치고 `meetings` 폴더를 오른쪽 버튼으로 누른다.
2. **새 파일**을 누르고 이름을 `setup-이름.md`로 적는다. 예: `setup-chaeeun.md`
3. 아래 내용을 적고 `Ctrl` + `S`로 저장한다.

```
# 개발 환경 설정 확인

- 이름:
- Python 버전:
- MariaDB 버전:
- 표 8개 확인: O
- .env 만들기: O
```

### 3. 무엇이 바뀌었는지 본다

```
git status
```

`docs/meetings/setup-이름.md` 한 줄만 보여야 한다. **`.env`나 `.env.example`이 보이면 멈추고 팀장에게 알린다.**

### 4. 올릴 파일을 담는다

```
git add docs/meetings/setup-이름.md
```

아무 글자도 나오지 않으면 맞다.

### 5. 기록을 남긴다

```
git commit -m "chore: 개발 환경 설정 확인 (이름)"
```

`1 file changed`가 나오면 맞다.

### 6. GitHub에 올린다

```
git push -u origin chore/setup-이름
```

처음이면 GitHub 로그인 창이 뜬다. 자기 계정으로 로그인한다.

### 7. PR을 연다

1. 브라우저에서 https://github.com/semiproejct/Money_to_Home 을 연다.
2. 위쪽에 뜨는 노란 띠의 **Compare & pull request**를 누른다.
3. **base를 `develop`으로 바꾼다.** 기본값이 `main`이라 꼭 바꿔야 한다. 왼쪽의 `base:` 단추를 눌러 고른다.
4. 아래의 **Create pull request**를 누른다.

### 8. 팀장이 합친다

팀장이 PR을 열어 **Merge pull request**를 누른다. 보라색 `Merged`가 뜨면 끝이다.

### 9. 원래 브랜치로 돌아온다

```
git checkout develop
```

```
git pull
```

다른 사람이 올린 내용까지 내 PC로 받아진다.

## 확인

| 번호 | 확인할 것 | 방법 |
| --- | --- | --- |
| 1 | 올리기 권한이 있다. | 6번이 오류 없이 끝났다. |
| 2 | PR이 열렸다. | GitHub의 **Pull requests** 탭에 내 PR이 보인다. |
| 3 | 합쳐졌다. | PR에 보라색 `Merged`가 보인다. |
| 4 | 다른 사람 것도 받았다. | 9번 뒤 `docs/meetings`에 다른 팀원의 파일이 보인다. |

## 막히면

| 나온 글자 | 원인과 할 일 |
| --- | --- |
| `Please tell me who you are` | Git에 이름을 알려 준 적이 없다. 아래 "이름 알려 주기"를 하고 5번을 다시 한다. |
| `Permission denied`, `403` | 저장소에 쓰기 권한이 없다. 팀장에게 GitHub 아이디를 알려 주고, 초대 메일에서 수락을 누른다. |
| `fatal: not a git repository` | 프로젝트 폴더 밖이다. `cd C:\projects\Money_to_Home`을 적는다. |
| `already exists` (1번에서) | 같은 이름의 브랜치가 이미 있다. `git checkout chore/setup-이름`으로 들어간다. |
| 노란 띠가 안 보인다 (7번에서) | **Pull requests** 탭 > **New pull request**를 누르고, base는 `develop`, compare는 자기 브랜치로 고른다. |
| base를 `main`으로 열었다 | PR 화면의 제목 옆 **Edit**를 눌러 base를 바꾼다. |

### 이름 알려 주기

처음 한 번만 한다. 따옴표 안을 자기 것으로 바꾼다.

```
git config --global user.name "자기 이름"
```

```
git config --global user.email "GitHub에 가입한 메일"
```

## 앞으로 작업할 때

이번 연습과 똑같다. 이름만 달라진다.

| 단계 | 연습 | 실제 작업 |
| --- | --- | --- |
| 브랜치 이름 | `chore/setup-이름` | `feature/기능이름`. 예: `feature/loan-calc` |
| 커밋 메시지 | `chore: 개발 환경 설정 확인` | `feat: 대출 계산 함수 추가` |
| PR의 base | `develop` | `develop` |

지킬 것 네 가지

- 작업을 시작하기 전에 `git pull`로 최신 내용을 받는다.
- `git add .`처럼 전부 담지 않는다. **자기가 고친 파일만** 이름을 적어 담는다.
- 올리기 전에 `git status`로 `.env`가 없는지 본다.
- `main`과 `develop`에는 직접 올리지 않는다. 항상 PR로 보낸다.
