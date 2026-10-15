# MyPets_in_window

Orca 없이 실행하는 Windows용 바탕화면 펫. Python과 PySide6로 만들었습니다.

## 다운로드

[**Windows 실행 파일 다운로드 — MyPets.exe**](https://github.com/pup996/MyPets_in_window/releases/latest/download/MyPets.exe)

Windows 10/11 64비트(x64)용입니다. 파일 크기는 약 46MB이며, 다운로드한 `MyPets.exe`를 더블클릭하면 됩니다.
Python이나 Orca를 따로 설치할 필요가 없습니다. 기본 펫 2종도 실행 파일 안에 들어 있습니다.

[릴리스 목록 및 이전 버전](https://github.com/pup996/MyPets_in_window/releases)

## 사용법

- 펫을 드래그하면 위치를 옮길 수 있습니다.
- 펫을 우클릭하면 펫 선택, 동작 변경, 크기 조절, 일시정지, 종료 메뉴가 나옵니다.
- 펫은 일반 창보다 위에 표시됩니다. 전체 화면 게임 등의 위에 표시되는지는 실행 환경에 따라 다릅니다.
- 기본 제공 펫은 눈을 깜빡이는 강아지와 여러 표정이 바뀌는 강아지 2종입니다.
- 인터넷, Orca, AI 서비스 로그인 없이 동작합니다.

배포용 `dist/MyPets.exe`를 실행하면 됩니다. Python을 따로 설치할 필요가 없습니다.

## 개발 환경에서 실행

Windows 10/11, Python 3.10 이상을 사용합니다. 아래 명령은 프로젝트 폴더에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pet.py
```

## 실행 파일 만들기

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

결과물은 `dist/MyPets.exe`입니다. 기본 펫 이미지도 포함된 단일 실행 파일입니다.
Python과 Qt 런타임을 함께 포함하므로 소스보다 용량이 큽니다. 첫 실행 때 압축 해제로 잠시 시간이 걸릴 수 있습니다.
Windows 실행 파일은 Windows에서 빌드합니다.

## 펫 추가

우클릭 메뉴의 **펫 선택 → 다른 pet.json 열기…**로 기존 Orca 펫 설정을 열 수 있습니다.
이 선택은 현재 실행 중에만 유지됩니다. 기본 펫을 바꾸려면 `pets` 폴더의 파일을 변경하세요.
자동 탐색은 `pets/폴더이름/pet.json` 구조를 사용하며 `puppy-emotions`를 우선 표시합니다.
실행 파일 옆에 `pets` 폴더를 두면 내장 펫 대신 해당 폴더를 읽습니다.

```text
pets/
  my-pet/
    pet.json
    spritesheet.png
```

설정 예시:

```json
{
  "displayName": "내 펫",
  "spritesheetPath": "spritesheet.png",
  "frame": { "width": 304, "height": 304 },
  "fps": 8,
  "defaultAnimation": "idle",
  "animations": {
    "idle": { "row": 0, "frames": 4, "frameDurationsMs": [2000, 100, 100, 2000] }
  }
}
```

PNG는 투명 배경을 사용합니다. 한 행에 프레임을 왼쪽부터 배치하고, `row`는 0부터 셉니다.
`frameDurationsMs`를 생략하면 `fps`를 사용합니다. 프레임별 재생 시간을 지정하면 `fps`보다 우선합니다.
이 프로그램은 이미 만들어진 펫을 재생합니다. 펫 이미지 생성이나 Orca 작업 상태 연동 기능은 포함하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
