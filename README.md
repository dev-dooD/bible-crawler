# Bible Crawler (bskorea.or.kr)

이 프로젝트는 대한성서공회(bskorea.or.kr)에서 제공하는 **개역개정(GAE)** 및 **새번역(SAENEW)** 성경 데이터를 크롤링하여 JSON 형식으로 저장하는 Python 스크립트입니다.

## 기능 (Features)
- **두 가지 역본 동시 수집**: 개역개정(GAE)과 새번역(SAENEW)을 병렬로 수집하여 매핑합니다.
- **소제목 추출**: 각 절 내부에 포함되거나 독립된 소제목을 추출하여 `subtitle` 필드로 구조화합니다.
- **각주 및 불필요한 태그 제거**: 본문에 포함된 각주 번호(예: `1)`)와 관주 링크 등을 완벽하게 제거하여 순수한 성경 본문만 저장합니다.
- **합쳐진 절 처리**: "18-19절"과 같이 합쳐진 절을 분리하고, 이후 절에는 참조 텍스트(`(18절에 포함)`)를 자동 생성하여 데이터의 연속성을 보장합니다.
- **이어받기 (Resume)**: 크롤링 중단 시, 이미 수집된 챕터는 건너뛰고 이어서 진행하여 데이터 중복을 방지합니다.
- **자동 재시도 및 에러 처리**: 네트워크 오류 발생 시 안정적인 수집을 위해 예외 처리가 적용되어 있습니다.

## 필요 라이브러리 (Prerequisites)
Python 3.x 환경에서 실행되며, 다음 라이브러리가 필요합니다.

```bash
pip install requests beautifulsoup4
```

## 사용 방법 (Usage)

### 1. 크롤링 실행
성경 66권 전체를 크롤링하여 `bible_data.json` 파일을 생성합니다.

```bash
python bible_crawler.py
```
- 실행 중 `crawler.log`에 진행 상황이 기록됩니다.
- 예상 소요 시간: 약 20~30분

### 2. 데이터 검증
수집된 데이터의 무결성을 검증합니다.

```bash
python deep_verify_data.py
```

## 데이터 구조 (Data Structure)

`bible_data.json`의 구조는 다음과 같습니다.

```json
{
  "metadata": {
    "source": "https://www.bskorea.or.kr",
    "versions": ["GAE", "SAENEW"],
    "crawled_at": "YYYY-MM-DD HH:MM:SS"
  },
  "books": [
    {
      "id": "gen",
      "name": "창세기",
      "chapters": [
        {
          "chapter": 1,
          "verses": [
            {
              "verse": 1,
              "text": {
                "GAE": "태초에 하나님이...",
                "SAENEW": "태초에 하나님이..."
              },
              "subtitle": {
                "GAE": "천지 창조",
                "SAENEW": "천지 창조"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## 알려진 특이사항 (Known Correct Behaviors)
데이터 검증 시 발견되는 다음 항목들은 오류가 아닌 **성경 원본의 특성**입니다.

1.  **새번역(SAENEW) 빈 절**: 마태복음 17:21, 18:11 등 일부 절은 원문 사본의 차이로 생략되어 빈 값(`""`)으로 저장됩니다.
2.  **사도행전 24:7 누락**: 텍스트수용본(Textus Receptus) 차이로 인해 해당 번역본에서 7절이 완전히 제외되어 있습니다.
3.  **요한계시록 12:18 (개역개정)**: 12:18의 내용이 12:17의 끝부분에 포함되어 있어, GAE 버전의 12:18은 빈 값입니다.
