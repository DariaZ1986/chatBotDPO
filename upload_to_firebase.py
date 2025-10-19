import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

def upload_to_firebase():
    try:
        # Инициализация Firebase
        cred_path = 'accountKey.json'
        
        if not os.path.exists(cred_path):
            print(f"❌ Файл {cred_path} не найден!")
            print("Убедитесь, что вы скачали serviceAccountKey.json из Firebase Console")
            return
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Чтение JSON файла
        json_path = 'programs.json'
        if not os.path.exists(json_path):
            print(f"❌ Файл {json_path} не найден!")
            return
            
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        print('🚀 Начинаем загрузку данных в Firebase...')
        
        total_directions = len(data['directions'])
        total_programs = sum(len(direction['programs']) for direction in data['directions'])
        
        print(f'📊 Найдено: {total_directions} направлений, {total_programs} программ')
        
        # Загрузка направлений и программ
        for i, direction in enumerate(data['directions'], 1):
            direction_ref = db.collection('directions').document(direction['id'])
            
            # Создаем объект направления без программ
            direction_data = {
                'id': direction['id'],
                'name': direction['name']
            }
            
            direction_ref.set(direction_data)
            print(f'✅ [{i}/{total_directions}] Направление: {direction["name"]}')
            
            # Загружаем программы для этого направления
            for j, program in enumerate(direction['programs'], 1):
                program_ref = direction_ref.collection('programs').document(program['id'])
                program_data = {
                    **program,
                    'directionId': direction['id'],
                    'directionName': direction['name']
                }
                program_ref.set(program_data)
                print(f'   📚 Программа [{j}/{len(direction["programs"])}]: {program["name"]}')
        
        print('🎉 Все данные успешно загружены в Firebase!')
        
    except Exception as e:
        print(f'❌ Произошла ошибка: {e}')

if __name__ == '__main__':
    upload_to_firebase()