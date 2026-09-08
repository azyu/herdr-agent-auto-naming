# herdr-agent-auto-naming

Herdr가 인식한 모든 에이전트에게 부르기 쉬운 두 단어 이름을 붙이고, 그 이름을 pane label에 남깁니다.

[![Herdr](https://img.shields.io/badge/herdr-0.9.0%2B-0797ff?logo=terminal&logoColor=white)](https://herdr.dev)
[![Python](https://img.shields.io/badge/python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Linux-lightgrey)](#설치)

English: [README.md](README.md)

에이전트에게 말을 걸 수 있게 이름을 붙여주는 [Herdr](https://herdr.dev) 플러그인입니다.
`herdr agent prompt green-cow "rebase onto main"`은 외워서 칠 수 있는 명령이지만,
`herdr agent prompt w15:p8 "..."`은 매번 찾아봐야 합니다.

런타임별 세션 훅이 아니라 Herdr의 `pane.agent_detected` 이벤트에 붙어 있습니다. 그래서
claude, codex, omp, agy, droid — Herdr가 에이전트로 분류하는 건 전부 — 각 에이전트 쪽에
아무것도 설치하지 않고 이름을 붙입니다.

이름은 에이전트뿐 아니라 **pane label**에도 씁니다. 에이전트 이름은 에이전트와 함께 사라지지만
label은 남습니다. 그래서 이미 알고 있는 패널에 에이전트가 다시 뜨면 새 이름이 아니라 원래 쓰던
이름을 돌려받습니다.

## 설치

Herdr 0.9.0 이상과 `python3`(표준 라이브러리만 사용)가 필요합니다. macOS, Linux 지원.

```sh
herdr plugin install azyu/herdr-agent-auto-naming
```

로컬에서 수정하며 쓰려면:

```sh
herdr plugin link /path/to/herdr-agent-auto-naming
```

설치 즉시 동작합니다. 서버를 재시작할 필요 없이, Herdr가 다음으로 인식하는 에이전트부터
이벤트 훅이 걸립니다. 설치 시점에 이미 떠 있던 에이전트는 한 번 훑어줘야 이름이 붙습니다.

```sh
herdr plugin action invoke azyu.agent-auto-naming.name-all
```

`herdr plugin list`로 설치 상태를,
`herdr plugin disable azyu.agent-auto-naming`으로 끄고,
`herdr plugin log list --plugin azyu.agent-auto-naming`으로 지금까지 붙인 이름을 볼 수 있습니다.

## 어떤 이름이 붙나

```
w15:p1  claude   →  green-cow
w15:p8  claude   →  crispy-toast
w17:p1  agy      →  orange-tapir
w19:p1  codex    →  white-fox
```

`<왼쪽>-<오른쪽>` 형태이고, 두 단어 목록의 합집합에서 뽑습니다 — 색 × 동물, 형용사 × 음식.
총 392개이고, 이미 쓰이는 이름은 두 번 나오지 않습니다.

| 계기 | 이름을 붙이는 대상 |
| --- | --- |
| `pane.agent_detected` | 이벤트에 실려온 패널 — 새로 뜬 에이전트, 또는 다시 나타난 에이전트. |
| startup 훅 | Herdr 서버가 세션을 복원할 때, 이름 없는 에이전트 전부. |
| `name-all` 액션 | 필요할 때 직접 실행, 이름 없는 에이전트 전부. |

## 건드리지 않는 것

- **이미 이름이 있는 에이전트.** `herdr agent start reviewer …`로 붙인 이름은 의도가 있는
  이름입니다. 그대로 두고, 에이전트가 종료돼도 살아남도록 pane label에만 복사해 둡니다.
- **직접 붙인 pane label.** Herdr의 에이전트 이름 규칙(`^[a-z][a-z0-9_-]{0,31}$`)에 맞는
  label은 재시작할 때마다 에이전트 이름으로 다시 묶입니다 — `green-cow`가 돌아오는 원리입니다.
  `Reviewer`처럼 규칙에 맞지 않는 label은 덮어쓰지 않고, 대신 그 에이전트를 이름 없이 둡니다.
- **다른 패널이 쓰고 있는 이름.** `agent_name_taken`이면 다시 뽑고, `herdr agent rename`이
  받아준 뒤에야 label을 씁니다. 경합에서 져도 남의 이름을 들고 있는 패널이 생기지 않습니다.

## 설정

설정은 없습니다. 바꿀 만한 건 단어 목록 하나뿐이고,
[`auto_name.py`](auto_name.py) 맨 위에 있습니다.

```python
THEMES = [
    ("white black orange ...".split(), "fox cow cat ...".split()),
    ("crispy salty spicy ...".split(), "toast miso ramen ...".split()),
]
```

`THEMES`는 `(왼쪽, 오른쪽)` 쌍의 목록이고 이름은 모든 테마의 합집합에서 나옵니다. 테마를
추가하면 기존 조합을 밀어내는 게 아니라 풀이 넓어집니다. 단어는 전부 소문자 ASCII로 쓰세요.
Herdr의 이름 규칙을 벗어난 이름은 애초에 배정되지 않습니다.

## 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 에이전트에 이름이 안 붙음 | `herdr agent get <pane>`. `agent_not_found`면 Herdr가 아직 분류하지 못한 상태라 이벤트 자체가 없었던 겁니다. 인식된 뒤에 `name-all`을 한 번 돌리세요. |
| 특정 패널만 계속 이름이 없음 | label이 에이전트 이름 규칙에 안 맞을 가능성이 큽니다. `herdr pane get <pane>`으로 확인하세요. `Reviewer` 같은 label은 덮어쓰지 않고 존중합니다. 넘기려면 `herdr pane rename <pane> --clear`. |
| 재시작 후 이름이 뒤바뀐 것 같음 | 기준은 pane label입니다. label과 에이전트 이름이 다르면 다음 인식 때 label이 이깁니다. |
| 한 패널에 두 이름이 경합함 | 다른 데서도 이름을 붙이고 있다는 뜻입니다. Herdr 이름을 배정하는 런타임별 `SessionStart` 훅이 있다면 이 플러그인과 충돌합니다. 둘 중 하나만 채번하게 두세요. |
| 아무 일도 일어나지 않음 | `herdr plugin list` — link만 하고 disable된 상태일 수 있습니다. 그다음 `herdr plugin log list --plugin azyu.agent-auto-naming`으로 마지막 실행과 stderr를 보세요. |

## 안전성

- `HERDR_BIN_PATH`를 통해 Herdr의 `agent`/`pane` API만 씁니다. 터미널 출력, 트랜스크립트,
  에이전트 상태는 읽지 않습니다.
- 어떤 에이전트에도 프롬프트나 키 입력을 보내지 않습니다.
- Herdr 밖으로는 아무것도 쓰지 않습니다 — 설정 파일도, state 디렉터리도, 네트워크도 없습니다.
- Python 표준 라이브러리만 사용합니다. 설치하거나 신뢰해야 할 의존성이 없습니다.

## 라이선스

MIT. Herdr와 무관한 개인 프로젝트입니다.
