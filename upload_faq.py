import firebase_admin
from firebase_admin import credentials, firestore
import json

def upload_faq():
    # Инициализация Firebase
    cred = credentials.Certificate('accountKey.json')
    firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    # Чтение FAQ JSON файла
    with open('faq.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    print('Начинаем загрузку FAQ в Firebase...')
    
    # Загрузка FAQ в коллекцию 'faq_categories'
    for i, category in enumerate(data['faq'], 1):
        category_id = f"category_{i}"
        category_data = {
            'id': category_id,
            'name': category['category'],
            'order': i
        }
        
        # Сохраняем категорию
        category_ref = db.collection('faq_categories').document(category_id)
        category_ref.set(category_data)
        print(f'✅ [{i}/{len(data["faq"])}] Категория: {category["category"]}')
        
        # Сохраняем вопросы этой категории
        for j, question in enumerate(category['questions'], 1):
            question_id = f"faq_{i}_{j}"
            question_data = {
                'id': question_id,
                'category_id': category_id,
                'category_name': category['category'],
                'question': question['q'],
                'answer': question['a'],
                'order': j
            }
            
            question_ref = db.collection('faq_questions').document(question_id)
            question_ref.set(question_data)
            print(f'   📝 Вопрос [{j}]: {question["q"][:50]}...')
    
    print('🎉 FAQ успешно загружен в Firebase!')

if __name__ == '__main__':
    upload_faq()