# 🏠 자취를 시작하려는 동국대생을 위한 부동산 상담 챗봇
2025-1학기 비어플 프로젝트 – BAF Chatbot

전세사기 피해 예방과 정보 불균형 해소를 위한 실용형 챗봇 서비스

## 📌 프로젝트 개요
팀명: BAF 챗봇팀

## 프로젝트명: 자취를 시작하려는 동국대생을 위한 부동산 상담 챗봇

## 목표: 자취를 시작하는 대학생에게 필요한 정보 제공 및 전세 사기 예방

### 🛠 주요 기능
📌 매물 추천	예산 및 옵션(에어컨 등)을 기준으로 조건에 맞는 방 목록 추천
📘 자취 가이드	계약 시 주의사항, 옵션 설명, 비용 절약 팁 등 PDF 기반 RAG 시스템
💬 실시간 응답	사용자의 자연어 질의에 대화형 방식으로 실시간 정보 제공

### 📂 활용 데이터셋
1. 📊 직방 크롤링 데이터 (CSV)
약 2,300건의 서울 3·4·6호선 주변 매물

보증금, 월세, 옵션, 거리 등 30+ 변수

구조화된 수치/범주형 데이터 → 매물 추천에 사용

2. 📄 자취백과사전 PDF
자취남 유튜버의 실용 가이드북 (232p)

계약, 옵션, 생활 정보 등 문서 기반 지식 → RAG 응답에 활용

### ⚙️ 기술 구현

![image](https://github.com/user-attachments/assets/dec85a25-3f99-4dc0-8677-60fedd08ccc5)

![image](https://github.com/user-attachments/assets/5baa4089-10a3-46d8-b824-9e4a87cc9e8a)

![image](https://github.com/user-attachments/assets/080ebb8f-e3aa-4e69-b2f1-35baa4172fc1)


## 🔍 20260331 수정사항

### 1. 벡터스토어 FAISS → Chroma 교체

- 메타데이터 수치 필터링 지원을 위해 변경
- 보증금, 월세, 소요시간 등 수치 조건을 DB 레벨에서 필터링

### 2. OpenAI → 무료 모델로 교체

- 임베딩: HuggingFaceEmbeddings (paraphrase-multilingual-MiniLM-L12-v2)
- LLM: ChatOllama (qwen2.5) → 한국어 성능 개선

### 3. SelfQueryRetriever 도입

- 기존 정규표현식 필터 (extract_deposit_limit, build_chroma_filter) 제거
- LLM이 자동으로 질문 분석 → 메타데이터 필터 생성
- 메타데이터 속성명 한글 → 영어로 변경 (유니코드 깨짐 방지)

### 4. 질의 분류 개선 (classify_query)

- 기존 키워드 방식 → 키워드 + LLM 하이브리드 방식
- 명확한 키워드면 즉시 분류, 애매할 때만 LLM 호출

### 5. 벡터스토어 캐싱

- 매 실행마다 새로 생성하던 방식 → 저장된 거 있으면 불러오기



