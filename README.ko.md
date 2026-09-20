# herdr-agent-auto-naming

Herdr가 감지한 모든 에이전트에 기억하기 쉬운 두 단어 이름을 붙이고,
그 이름을 pane label로 보존합니다.

[![Herdr](https://img.shields.io/badge/herdr-0.9.0%2B-0797ff?logo=terminal&logoColor=white)](https://herdr.dev)
[![Python](https://img.shields.io/badge/python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Linux-lightgrey)](#설치)

영문 문서: [README.md](README.md)

에이전트에게 말을 걸기 쉬운 이름을 붙여 주는 [Herdr](https://herdr.dev) 플러그인입니다.
`herdr agent prompt green-cow "rebase onto main"`은 외워서 입력할 수 있지만,
`herdr agent prompt w15:p8 "..."`은 쓸 때마다 찾아봐야 합니다.

런타임별 세션 훅 대신 Herdr의 `pane.agent_detected` 이벤트를 사용합니다. 따라서 claude,
codex, omp, agy, droid를 비롯해 Herdr가 에이전트로 분류하는 모든 대상에 이름을 붙입니다.
각 에이전트에 따로 설치할 것은 없습니다. 알아둘 경우는 `/clear`·`/new`처럼 세션을
제자리에서 교체하는 경우 하나입니다.
[`/clear`와 `/new`는 이름을 지웁니다](#clear와-new는-이름을-지웁니다)를 보세요.

이름은 에이전트뿐 아니라 **pane label**에도 기록합니다. 에이전트 이름은 에이전트가
종료되면 사라지지만 label은 남습니다. 같은 패널에 에이전트가 다시 나타나면 새 이름 대신
기존 이름을 돌려받습니다.

## 설치

Herdr 0.9.0 이상과 `python3`가 필요합니다. Python 표준 라이브러리만 사용하며
macOS와 Linux를 지원합니다.

```sh
herdr plugin install azyu/herdr-agent-auto-naming
```

로컬에서 수정하면서 사용하려면:

```sh
herdr plugin link /path/to/herdr-agent-auto-naming
```

설치하면 바로 동작합니다. 서버를 재시작하지 않아도 Herdr가 다음 에이전트를 감지하는 순간부터
이벤트 훅이 실행됩니다. 설치 전에 이미 실행 중이던 에이전트에는 `name-all`을 한 번 실행하세요.

```sh
herdr plugin action invoke azyu.agent-auto-naming.name-all
```

`herdr plugin list`로 설치 상태를 확인할 수 있습니다. 플러그인을 끄려면
`herdr plugin disable azyu.agent-auto-naming`을 실행하세요. 지금까지 붙인 이름은
`herdr plugin log list --plugin azyu.agent-auto-naming`에서 확인할 수 있습니다.

## 이름을 붙이는 방식

<img src="docs/screenshots/pane-names.png" alt="crimson-crane과 frosty-miso로 이름 붙은 Herdr 패널 두 개" width="820">

이름은 `<왼쪽>-<오른쪽>` 형식입니다. 색 × 동물, 형용사 × 음식으로 구성된 두 테마에서
조합을 뽑습니다. 총 392개이며 이미 사용 중인 이름은 다시 배정하지 않습니다. 이름은
패널 제목에도 표시되므로 명령을 입력하기 전에 화면에서 확인할 수 있습니다.

| 실행 시점 | 이름을 붙이는 대상 |
| --- | --- |
| `pane.agent_detected` | 이벤트에 포함된 패널. 새로 실행됐거나 다시 나타난 에이전트입니다. |
| `pane.agent_status_changed` | 이벤트에 포함된 패널. 이름을 잃은 에이전트가 다시 작업을 시작한 시점입니다. |
| startup 훅 | Herdr 서버가 세션을 복원할 때 이름이 없는 모든 에이전트 |
| `name-all` 액션 | 사용자가 직접 실행할 때 이름이 없는 모든 에이전트 |

## `/clear`와 `/new`는 이름을 지웁니다

두 명령은 에이전트를 재시작하지 않고 같은 프로세스 안에서 세션만 교체합니다. Herdr는
교체된 세션을 새 에이전트로 보고 이름을 지우기 때문에 pane label은 남아 있는데
사이드바만 런타임 이름인 `claude`로 되돌아갑니다. 이때 Herdr는 감지 이벤트를 보내지
않습니다. `pane.agent_status_changed`를 구독하는 이유가 이것입니다. 교체 이후 처음
도착하는 이벤트이고 label은 그대로 남아 있어 다시 묶을 수 있습니다. Herdr 0.9.1에서
측정한 결과입니다.

| 런타임 | 이름이 지워지는 시점 | 복구 주체 |
| --- | --- | --- |
| codex `/new` | 직후 첫 프롬프트에서 새 세션이 보고될 때 | 플러그인이 같은 턴에 복구 |
| omp `/new` | 즉시 | 플러그인이 1초 이내에 복구 |
| Claude Code `/clear`, `/new` | 즉시 | 플러그인이 다음 상태 변화에 복구 — 실제로는 도구를 쓰는 다음 턴입니다 |

Claude Code만 느린 이유는 Herdr가 이 런타임의 상태를 화면에서 읽기 때문입니다. 텍스트만
출력하는 턴은 제 측정에서 한 번도 `working`으로 잡히지 않았습니다. 13초짜리도, 800줄
짜리도 마찬가지였습니다. 그래서 플러그인이 기다리는 상태 이벤트는 에이전트가 파일을
읽거나 명령을 실행할 때까지 오지 않고, 그동안 패널은 `claude`로 남습니다. 이것은
`/clear`와 무관하며 한 번도 건드리지 않은 패널도 똑같습니다. 패널 하단의 커스텀
statusline이 영향을 줬을 가능성도 있습니다. 당장 되돌리려면 `name-all`을 쓰세요.

```sh
herdr plugin action invoke azyu.agent-auto-naming.name-all
```

`/clear`하는 순간 바로 이름을 되찾고 싶다면 `~/.claude/settings.json`의
`hooks.SessionStart`에 아래를 추가하세요. 이름을 직접 배정하지 않고 이 플러그인의
액션만 호출하므로 이름 발급이 경합하지 않습니다.

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "if [ \"${HERDR_ENV:-}\" = \"1\" ] && command -v herdr >/dev/null 2>&1; then (sleep 1; herdr plugin action invoke azyu.agent-auto-naming.name-all >/dev/null 2>&1 &) ; fi; exit 0",
      "timeout": 5
    }
  ]
}
```

`sleep 1`이 필요한 이유는 Claude Code가 `SessionStart` 훅들을 병렬로 실행하기
때문입니다. 이것이 없으면 Herdr가 세션 보고를 처리하기 전에 스윕이 끝나 곧 지워질
이름을 다시 붙이고 마는 경우가 생깁니다. Herdr 자체 훅은 500ms 후 포기하므로 1초면
충분합니다.

## 그대로 두는 것

- **이미 이름이 있는 에이전트.** `herdr agent start reviewer …`로 지정한 이름은 그대로
  둡니다. 에이전트가 종료된 뒤에도 이름이 남도록 pane label에만 복사합니다.
- **사용자가 직접 붙인 pane label.** Herdr의 에이전트 이름 규칙
  (`^[a-z][a-z0-9_-]{0,31}$`)에 맞는 label은 재시작할 때마다 에이전트 이름으로 다시
  연결됩니다. `green-cow`가 돌아오는 이유입니다. `Reviewer`처럼 규칙에 맞지 않는 label도
  덮어쓰지 않습니다. 이 경우 에이전트에는 이름을 붙이지 않습니다.
- **다른 패널이 사용 중인 이름.** `agent_name_taken`이 발생하면 다른 이름을 뽑습니다.
  `herdr agent rename`이 이름을 받아들인 뒤에만 label을 기록하므로, 경합에서 져도 패널에
  다른 에이전트의 이름이 남지 않습니다.

## 설정

별도 설정은 없습니다. 바꿀 수 있는 것은 단어 목록뿐이며,
[`auto_name.py`](auto_name.py) 맨 위에 있습니다.

```python
THEMES = [
    ("white black orange ...".split(), "fox cow cat ...".split()),
    ("crispy salty spicy ...".split(), "toast miso ramen ...".split()),
]
```

`THEMES`는 `(왼쪽, 오른쪽)` 쌍의 목록입니다. 이름은 각 테마에서 만든 조합의 합집합에서
뽑습니다. 테마를 추가하면 기존 조합은 그대로 두고 후보만 늘어납니다. 모든 단어는 소문자 ASCII로
작성하세요. Herdr의 이름 규칙에 맞지 않는 이름은 배정하지 않습니다.

## 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 에이전트에 이름이 붙지 않음 | `herdr agent get <pane>`을 실행하세요. `agent_not_found`라면 Herdr가 아직 에이전트로 분류하지 않아 이벤트가 발생하지 않은 상태입니다. Herdr가 에이전트로 감지한 뒤 `name-all`을 한 번 실행하세요. |
| 특정 패널에 계속 이름이 붙지 않음 | label이 에이전트 이름 규칙에 맞지 않을 수 있습니다. `herdr pane get <pane>`으로 확인하세요. `Reviewer` 같은 label은 덮어쓰지 않습니다. 자동으로 이름을 붙이려면 `herdr pane rename <pane> --clear`로 label을 지우세요. |
| 재시작 후 이름이 바뀐 것처럼 보임 | pane label이 기준입니다. label과 에이전트 이름이 다르면 다음에 감지될 때 label을 따릅니다. |
| 한 패널에서 두 이름이 경합함 | 다른 곳에서도 이름을 붙이고 있다는 뜻입니다. Herdr 이름을 배정하는 런타임별 `SessionStart` 훅은 이 플러그인과 충돌합니다. 둘 중 하나만 이름을 붙이도록 설정하세요. |
| Claude Code 패널이 다시 `claude`로 보임 | 그 패널에서 `/clear` 또는 `/new`를 실행한 경우입니다. 도구를 쓰는 다음 턴에 돌아오고, 즉시 복구하려면 `herdr plugin action invoke azyu.agent-auto-naming.name-all`을 실행하세요. |
| Claude Code 패널이 답변 중인데 `idle`로 보임 | Herdr는 Claude Code의 상태를 화면에서 읽는데, 텍스트만 출력하는 턴은 작업으로 보이지 않습니다. 도구를 쓰는 다음 턴에서 따라잡습니다. 이름 문제는 아니지만, `/clear`한 패널이 한동안 `claude`로 남는 이유입니다. |
| 아무 일도 일어나지 않음 | `herdr plugin list`로 플러그인이 비활성화됐는지 확인하세요. 그다음 `herdr plugin log list --plugin azyu.agent-auto-naming`에서 최근 실행 기록과 stderr를 확인하세요. |

## 안전성

- `HERDR_BIN_PATH`를 통해 Herdr의 `agent`/`pane` API만 사용합니다. 터미널 출력,
  트랜스크립트, 에이전트 상태는 읽지 않습니다.
- 어떤 에이전트에도 프롬프트나 키 입력을 보내지 않습니다.
- Herdr 외부에는 아무것도 쓰지 않습니다. 설정 파일과 state 디렉터리를 만들지 않고
  네트워크도 사용하지 않습니다.
- Python 표준 라이브러리만 사용하므로 별도로 설치하거나 신뢰할 의존성이 없습니다.

## 라이선스

MIT 라이선스를 따릅니다. Herdr와 무관한 개인 프로젝트입니다.
