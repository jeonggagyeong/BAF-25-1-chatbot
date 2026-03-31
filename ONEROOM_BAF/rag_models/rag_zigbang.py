import os
import json
import re
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo


# ✅ 환경 설정 (OpenAI 키 불필요)
embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

llm = ChatOllama(model="llama3", temperature=0)

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

            description  = safe_get(content, '설명')
            title        = safe_get(content, '제목')
            location     = safe_get(content, '주소(법정동)')
            deposit      = safe_get(content, '보증금(만원)')
            rent         = safe_get(content, '월세(만원)')
            area         = safe_get(content, '전용면적(m²)')
            room_type    = safe_get(content, '방종류')
            room_layout  = safe_get(content, '룸타입')
            parking      = safe_get(content, '주차여부')
            floor        = safe_get(content, '층수')
            options      = safe_get(content, '옵션')
            available_date  = safe_get(content, '입주가능일')
            nearest_station = safe_get(content, '가장가까운역')

            time_to_chungmuro = safe_int(content.get('매물_부터_충무로1출까지_시간_분'))
            time_to_dongguk   = safe_int(content.get('매물_부터_동입6출까지_시간_분'))

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
                "id":           str(content.get("매물ID", "")),
                "deposit":      safe_int(content.get("보증금(만원)")),      # 보증금
                "rent":         safe_int(content.get("월세(만원)")),        # 월세
                "area":         safe_int(content.get("전용면적(m²)")),      # 면적
                "chungmuro_min": time_to_chungmuro,                        # 충무로 소요시간
                "dongguk_min":   time_to_dongguk,                          # 동대입구 소요시간
                "source":       "json"
}

            ))
        except Exception as e:
            print("❌ 변환 실패:", e)
    return documents

def load_json_to_documents(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    id_to_raw = {entry.get("매물ID"): entry for entry in raw_data}
    raw_docs = [
        Document(page_content=json.dumps(entry), metadata={"매물ID": entry.get("매물ID")})
        for entry in raw_data
    ]
    converted_docs = convert_json_docs_to_text(raw_docs)
    return converted_docs, id_to_raw


def classify_query(query: str):
    # 1단계: 명확한 키워드면 바로 분류
    clear_housing = ["원룸", "투룸", "쓰리룸", "오피스텔", "빌라", "월세", "매물", "입주", "역세권", "도보"]
    clear_legal   = ["소송", "분쟁", "전세사기", "확정일자", "전입신고", "권리금", "위약금", "임대인", "임차인"]

    if any(k in query for k in clear_housing):
        print(" 키워드 분류 → 매물검색")
        return "csv"
    if any(k in query for k in clear_legal):
        print(" 키워드 분류 → 법률정보")
        return "pdf"

    # 2단계: 애매할 때만 LLM 호출
    print(" 애매한 질문 → LLM 분류 중...")
    response = llm.invoke(f"""
다음 질문이 어떤 유형인지 판단하세요.

유형 기준:
- 매물검색: 방, 원룸, 투룸, 보증금, 월세, 역세권, 면적, 주차, 입주 등 매물 조건 검색
- 법률정보: 계약, 분쟁, 소송, 전세사기, 중개수수료, 권리금, 해지 등 법률/계약 관련

질문: {query}
반드시 "매물검색" 또는 "법률정보" 중 하나만 답하세요. 다른 말은 하지 마세요.
""")
    result = response.content.strip()
    print(f"🔍 LLM 분류 결과: {result}")
    if "매물검색" in result:
        return "csv"
    return "pdf"



def get_csv_qa(json_path, vector_path, query):
    # 벡터스토어 로딩 또는 생성
    if os.path.exists(vector_path):
        print(" 기존 벡터스토어 로딩")
        vs = Chroma(persist_directory=vector_path, embedding_function=embedding)
    else:
        print("🔨 벡터스토어 새로 생성")
        docs, _ = load_json_to_documents(json_path)
        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        split_docs = splitter.split_documents(docs)
        vs = Chroma.from_documents(split_docs, embedding, persist_directory=vector_path)
        vs.persist()

    # ✅ Self-Query Retriever: LLM이 자동으로 필터 생성
    metadata_field_info = [
        AttributeInfo(name="deposit",      description="보증금 만원 단위 숫자", type="integer"),
        AttributeInfo(name="rent",         description="월세 만원 단위 숫자",  type="integer"),
        AttributeInfo(name="area",         description="전용면적 m² 단위",     type="integer"),
        AttributeInfo(name="chungmuro_min", description="충무로역까지 도보 소요시간(분)", type="integer"),
        AttributeInfo(name="dongguk_min",   description="동대입구역까지 도보 소요시간(분)", type="integer"),
]

    retriever = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vs,
        document_contents="부동산 매물 정보",
        metadata_field_info=metadata_field_info,
        verbose=True       # ✅ 어떤 필터 만들었는지 출력
    )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
당신은 부동산 매물 추천을 도와주는 챗봇입니다.
다음은 매물 데이터입니다.
문서에 보증금, 거리 등의 조건이 언급되어 있으면 그에 맞는 매물을 골라서 부드럽고 자연스러운 말투로 간단히 요약해 설명해주세요.
반드시 한국어로만 답변하세요. 영어로 답변하지마세요.

[문서 내용]
{context}

[질문]
{question}

[답변]
"""
    )

    _, id_to_raw = load_json_to_documents(json_path)

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )

    return qa, id_to_raw


def get_pdf_qa(pdf_path, vector_path="./vectorstore_pdf"):
    if os.path.exists(vector_path):
        print(" 기존 PDF 벡터스토어 로딩")
        vectordb = Chroma(persist_directory=vector_path, embedding_function=embedding)
    else:
        print("🔨 PDF 벡터스토어 새로 생성")
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = []
        for doc in docs:
            page = doc.metadata.get("page")
            for chunk in splitter.split_text(doc.page_content):
                chunks.append(Document(
                    page_content=chunk,
                    metadata={"page": page, "source": "pdf"}
                ))
        vectordb = Chroma.from_documents(chunks, embedding, persist_directory=vector_path)
        vectordb.persist()

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
다음은 '자취백과사전'의 내용입니다.
반드시 아래 문서 내용에 기반하여 답변하세요. 문서에 없는 내용은 추측하지 마세요.
반드시 한국어로만 답변하세요. 영어로 답변하지마세요.

[문서 내용]
{context}

[질문]
{question}

[답변]
"""
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectordb.as_retriever(search_kwargs={"k": 4}),
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )
    return qa



def unified_chatbot(query: str):
    print(f"\n 사용자 질문: {query}")
    source = classify_query(query)

    if source == "csv":
        qa, id_to_raw = get_csv_qa("./data/매물_데이터.json", "./vectorstore_json", query)
        result = qa.invoke(query)

        allowed_ids = set(doc.metadata.get("매물ID") for doc in result['source_documents'])

        print("\n 매물 결과:")
        count = 0
        for doc in result['source_documents']:
            doc_id = doc.metadata.get("매물ID")
            if doc_id not in allowed_ids:
                continue
            raw = id_to_raw.get(doc_id, {})
            print(f"▶️ 매물 {count+1}")
            print(f"- 위치: {raw.get('주소(법정동)', '정보 없음')} / 보증금: {raw.get('보증금(만원)', '정보 없음')} / 월세: {raw.get('월세(만원)', '정보 없음')}만원")
            print(f"- 충무로역까지 시간: {raw.get('매물_부터_충무로1출까지_시간_분', '정보 없음')}분")
            print("-" * 40)
            count += 1

        print("\n LLM 응답:", result['result'])
    else:
        qa = get_pdf_qa(r"C:\\Users\\jeong\\baf_langchain\\data\\자취백과사전_2025 (1).pdf")
        result = qa.invoke(query)
        print("\n 자취백과 응답:", result['result'])
        print("\n 출처 문서:")
        for i, doc in enumerate(result['source_documents']):
            print(f"--- 출처 {i+1} ---\n{doc.page_content[:300]}\n")


if __name__ == "__main__":
    test_queries = [
        "보증금 500 이하 충무로역 10분 이내 원룸 알려줘"
    ]
    for q in test_queries:
        unified_chatbot(q)
        print("\n" + "=" * 80 + "\n")
