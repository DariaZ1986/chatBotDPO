import firebase_admin
from firebase_admin import credentials, firestore

def check_faq_data():
    cred = credentials.Certificate('accountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    
    print("🔍 Проверяем данные в Firebase...")
    
    # Проверяем категории
    categories = list(db.collection("faq_categories").stream())
    print(f"📁 Категорий найдено: {len(categories)}")
    
    for cat in categories:
        cat_data = cat.to_dict()
        print(f"  - {cat.id}: {cat_data.get('name', 'No name')}")
    
    # Проверяем вопросы
    questions = list(db.collection("faq_questions").stream())
    print(f"❓ Вопросов найдено: {len(questions)}")
    
    for q in questions[:5]:  # Покажем первые 5
        q_data = q.to_dict()
        print(f"  - {q.id}: {q_data.get('question', 'No question')[:50]}...")
    
    if len(questions) > 5:
        print(f"  ... и еще {len(questions) - 5} вопросов")

if __name__ == '__main__':
    check_faq_data()