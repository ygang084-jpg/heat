# 서울시 폭염대응시설 대시보드

무더위쉼터 · 그늘막 · 2025년 온열질환 신고현황(질병관리청 연보)을 통합한 Streamlit 대시보드.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud 배포에 필요한 파일

| 파일 | 용도 |
|------|------|
| `app.py` | 메인 앱 |
| `requirements.txt` | 의존성 (streamlit, pandas) |
| `서울시 무더위쉼터.csv` | 무더위쉼터 데이터 (cp949) |
| `폭염저감시설_그늘막_2026년.csv` | 그늘막 데이터 (utf-8-sig, 엑셀에서 변환) |
| `.streamlit/config.toml` | Streamlit 설정 (선택) |

> 온열질환 신고수/사망자수는 PDF 연보에서 추출해 `app.py` 상수로 반영되어 있어 별도 파일이 필요 없습니다.
> 원본 `.xlsx` / `.pdf` 는 런타임에 사용하지 않으므로 배포 대상에서 제외합니다(`.gitignore`).

## 배포 절차 (Streamlit Community Cloud)

1. 위 표의 파일들을 GitHub 저장소에 올립니다.
2. https://share.streamlit.io 접속 → **New app**
3. 저장소·브랜치 선택, **Main file path** 를 `app.py` 로 지정
4. **Deploy** 클릭
