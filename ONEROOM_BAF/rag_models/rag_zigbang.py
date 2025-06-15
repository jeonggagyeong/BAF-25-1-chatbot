import os
import json
import re
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores.faiss import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader

# 환경 설정
os.environ["OPENAI_API_KEY"] = "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"
embedding = OpenAIEmbeddings()

def safe_get(d, key):
    val = d.get(key, "")
    return str(val).strip().replace("\n", " ") if val is not None else ""

def safe_int(val):
    try:
        return int(val)
    except:
        return 999

def convert_json_docs_to_text(json_docs):
    documents = []
    for doc in json_docs:
        try:
            content = json.loads(doc.page_content) if isinstance(doc.page_content, str) else doc.page_content

            description = safe_get(content, '설명')
            title = safe_get(content, '제목')
            location = safe_get(content, '주소(법정동)')
            deposit = safe_get(content, '보증금(만원)')
            rent = safe_get(content, '월세(만원)')
            area = safe_get(content, '전용면적(m²)')
            room_type = safe_get(content, '방종류')
            room_layout = safe_get(content, '룸타입')
            parking = safe_get(content, '주차여부')
            floor = safe_get(content, '층수')
            options = safe_get(content, '옵션')
            available_date = safe_get(content, '입주가능일')
            nearest_station = safe_get(content, '가장가까운역')

            time_to_chungmuro = safe_int(content.get('매물_부터_충무로1출까지_시간_분'))
            time_to_dongguk = safe_int(content.get('매물_부터_동입6출까지_시간_분'))

            text = f"""
[{title}]
- 설명: {description}
- 위치: {location}
- 보증금/월세: {deposit}/{rent}만원
- 면적: {area}㎡
- 방종류: {room_type}, 룸타입: {room_layout}
- 주차: {parking}, 층수: {floor}
- 옵션: {options}
- 입주 가능일: {available_date}
- 가장 가까운 역: {nearest_station}
- 충무로역까지 시간: {time_to_chungmuro}분
- 동대입구역까지 시간: {time_to_dongguk}분
""".strip()

            documents.append(Document(
                page_content=text,
                metadata={
                    "매물ID": content.get("매물ID", ""),
                    "충무로_소요시간_분": time_to_chungmuro,
                    "동대입구_소요시간_분": time_to_dongguk
                }
            ))
        except Exception as e:
            print("❌ 변환 실패:", e)

    return documents

    
# 질의 분석 함수들
def extract_station_and_minutes(query: str):
    station_match = re.search(r'([가-힣]+)역', query)
    time_match = re.search(r'(\d+)\s*분\s*이내', query)
    return {
        "역": station_match.group(1) if station_match else None,
        "분": int(time_match.group(1)) if time_match else None
    }

def extract_deposit_limit(query: str):
    match = re.search(r'보증금\s*(\d{2,5})\s*만원\s*(이내|까지)?', query)
    return int(match.group(1)) if match else None

def classify_query(query: str):
    query = query.lower()
    legal_keywords = ["돌려받", "못 받", "소송", "계약", "파기", "법률", "문제", "분쟁", "주의사항"]
    housing_keywords = ["보증금", "월세", "역", "매물", "면적", "주차", "원룸", "투룸","주차","가까운"]
    if any(k in query for k in legal_keywords):
        return "pdf"
    elif any(k in query for k in housing_keywords):
        return "csv"
    return "pdf"

# 매물 JSON 로딩 및 필터링 처리
def load_json_to_documents(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    id_to_raw = {entry.get("매물ID"): entry for entry in raw_data}
    
    # JSON을 Document로 변환
    raw_docs = [
        Document(page_content=json.dumps(entry), metadata={"매물ID": entry.get("매물ID")})
        for entry in raw_data
    ]
    
    # 자연어 텍스트로 변환
    converted_docs = convert_json_docs_to_text(raw_docs)
    return converted_docs, id_to_raw



def normalize_station_name(name):
    return name.replace("역", "").strip() if name else ""

def filter_docs(docs, id_to_raw, query):
    parsed = extract_station_and_minutes(query)
    deposit_limit = extract_deposit_limit(query)
    station_name = normalize_station_name(parsed['역'])
    max_minutes = parsed['분'] if parsed['분'] else 999

    filtered = []
    for doc in docs:
        doc_id = doc.metadata.get("매물ID")
        raw = id_to_raw.get(doc_id, {})

        try:
            deposit = int(str(raw.get("보증금(만원)", "99999")).replace(",", ""))
            if deposit_limit and deposit > deposit_limit:
                continue
        except:
            continue

        time_value = doc.metadata.get(f"{station_name}_소요시간_분", 999)
        closest_station = normalize_station_name(raw.get("가장가까운역", ""))

        if station_name:
            is_close_by_name = station_name in closest_station
            is_within_time = time_value <= max_minutes
            if not (is_close_by_name or is_within_time):
                continue

        filtered.append(doc)

    return filtered



# CSV 기반 벡터스토어 생성 또는 로딩
def get_csv_qa(json_path, vector_path, query):
    docs, id_to_raw = load_json_to_documents(json_path)
    filtered_docs = filter_docs(docs, id_to_raw, query)

    if not filtered_docs:
        print("❗조건에 맞는 매물이 없습니다.")
        return None, id_to_raw

    print(f"🎯 조건에 맞는 매물 수: {len(filtered_docs)}")

    
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    split_docs = splitter.split_documents(filtered_docs)
    vs = FAISS.from_documents(split_docs, embedding)
    vs.save_local(vector_path)

    prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""
    당신은 부동산 매물 추천을 도와주는 챗봇입니다.
    다음은 매물 데이터입니다.
    문서에 보증금, 거리 등의 조건이 언급되어 있으면 그에 맞는 매물을 골라서 부드럽고 자연스러운 말투로 간단히 요약해 설명해주세요.
    

    
    


    [문서 내용]
    {context}

    [질문]
    {question}

    [답변]
    """
    )    

    qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(temperature=0),
    retriever=vs.as_retriever(search_kwargs={"k": 10}),
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt},  # 여기에 프롬프트 넣기
    return_source_documents=True
    )
    
    return qa, id_to_raw



# PDF 기반 벡터스토어 구성
def get_pdf_qa(pdf_path):
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = []
    for doc in docs:
        page = doc.metadata.get("page")
        for chunk in splitter.split_text(doc.page_content):
            chunks.append(Document(
                page_content=chunk,
                metadata={"page": page, "source": chunk[:30].strip().replace("\n", " ")}
            ))
    vectordb = FAISS.from_documents(chunks, embedding)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
다음은 '자취백과사전'의 내용입니다.
반드시 아래 문서 내용에 기반하여 답변하세요. 문서에 없는 내용은 추측하지 마세요.

[문서 내용]
{context}

[질문]
{question}

[답변]
"""
    )
    qa = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        retriever=vectordb.as_retriever(search_kwargs={"k": 4}),
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )
    return qa

# 통합 챗봇

def unified_chatbot(query: str):
    print(f"\n💬 사용자 질문: {query}")
    source = classify_query(query)
    if source == "csv":
        qa, id_to_raw = get_csv_qa("./data/매물_데이터.json", "./vectorstore", query)
        result = qa.invoke(query)

        # ✅ 조건에 맞는 매물 ID만 필터링
        allowed_ids = set(doc.metadata.get("매물ID") for doc in result['source_documents'])

        print("\n📦 매물 결과:")
        count = 0
        for i, doc in enumerate(result['source_documents']):
            doc_id = doc.metadata.get("매물ID")
            if doc_id not in allowed_ids:
                continue
            raw = id_to_raw.get(doc_id, {})
            print(f"▶️ 매물 {count+1}")
            print(f"- 위치: {raw.get('주소(법정동)', '정보 없음')} / 보증금: {raw.get('보증금(만원)', '정보 없음')} / 월세: {raw.get('월세(만원)', '정보 없음')}만원")
            print(f"- 충무로역까지 시간: {raw.get('매물_부터_충무로1출까지_시간_분', '정보 없음')}분")
            print("-" * 40)
            count += 1

        print("\n🧠 LLM 응답:", result['result'])
    else:
        qa = get_pdf_qa(r"C:\\Users\\jeong\\baf_langchain\\data\\자취백과사전_2025 (1).pdf")
        result = qa.invoke(query)
        print("\n📘 자취백과 응답:", result['result'])
        print("\n📄 출처 문서:")
        for i, doc in enumerate(result['source_documents']):
            print(f"--- 출처 {i+1} ---\n{doc.page_content[:300]}\n")

# 테스트
if __name__ == "__main__":
    test_queries = [
        "부동산 중개보수의 최고 요율이란 무엇을 의미하나요?"
        
       
    ]
    for q in test_queries:
        unified_chatbot(q)
        print("\n" + "=" * 80 + "\n")
