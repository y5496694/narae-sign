# 나래서명

Windows에서 마우스·펜으로 직접 서명하고 **서명 획만 투명 PNG**로 저장하는 작은 로컬 앱입니다. 서명이나 계정 정보는 서버로 보내지 않습니다.

## 실행

Python 3.10 이상(Tk 포함)을 설치한 뒤:

```powershell
python -m pip install -r requirements.txt
python signature.py
```

Windows에서는 `나래서명.cmd`를 더블 클릭해 실행할 수 있습니다.

1. 흰 영역에 서명합니다.
2. `한 획 취소` 또는 `다시 쓰기`로 수정합니다.
3. `확인 · PNG 저장`을 누릅니다.
4. 여백을 자르고 가장자리의 부드러움을 유지한 RGBA PNG가 저장됩니다. 흰 배경·안내문은 저장되지 않습니다.

문서 도구와 연결할 때 출력 경로와 저장 결과를 지정할 수 있습니다. 결과 JSON은 사용자가 직접 확인한 후에만 생성됩니다.

```powershell
python signature.py --output D:\Codex\signatures\signature.png --result D:\Codex\signatures\saved.json
```

서명 이미지와 사용자별 결과 파일은 Git에 포함하지 않습니다. 한글에 삽입할 때는 나래 한글 오피스의 서명 삽입 기능으로 위치·크기와 `글 뒤로` 배치를 지정합니다.

## 검증

```powershell
python -m unittest discover -s tests -v
```

실제 획 기반 투명 배경·크롭·안티앨리어싱·저장 검증·빈 서명 거부를 확인합니다. 테스트에는 개인 서명을 사용하지 않습니다.
