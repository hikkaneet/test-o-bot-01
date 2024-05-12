import aiosqlite
from aiogram import types

from kb import generate_options_keyboard
from data import quiz_data


async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Удаляем таблицу, если она существует
        await db.execute('DROP TABLE IF EXISTS quiz_state')
        # Выполняем SQL-запрос к базе данных
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (
                         user_id INTEGER PRIMARY KEY,
                         question_index INTEGER)''')
        # Сохраняем изменения
        await db.commit()


async def create_answers_table():
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Удаляем таблицу, если она существует
        await db.execute('DROP TABLE IF EXISTS all_answers')
        await db.execute('''CREATE TABLE IF NOT EXISTS all_answers (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER,
                         question_index INTEGER,
                         selected_option INTEGER,
                         is_correct INTEGER)''')
        await db.commit()


async def update_quiz_index(user_id, index):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        # Сохраняем изменения
        await db.commit()


async def get_quiz_index(user_id):
    # Подключаемся к базе данных
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def clear_answers_table(user_id):
    async with aiosqlite.connect('quiz_bot.db') as db:
        await db.execute(f"DELETE FROM all_answers WHERE user_id = {user_id}")
        await db.commit()


async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id

    # проверяем, есть ли уже пользователь с таким user_id в таблице all_answers
    async with aiosqlite.connect('quiz_bot.db') as db:
        cursor = await db.execute(f"SELECT COUNT(*) FROM all_answers WHERE user_id = {user_id}")
        row = await cursor.fetchone()
        user_exists = row[0] > 0

    # если пользователь уже есть, очищаем таблицу от его ответов
    if user_exists:
        await clear_answers_table(user_id)

    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)

    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)


async def get_question(message, user_id):
    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса
    correct_index = quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts, opts[correct_index])
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


async def remove_reply_markup(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )


async def process_answer(callback: types.CallbackQuery, is_correct: bool, answer_option: str):
    await remove_reply_markup(callback)

    current_question_index = await get_quiz_index(callback.from_user.id)

    if is_correct:
        await callback.message.answer("Верно!")
    else:
        correct_option = quiz_data[current_question_index]['correct_option']
        await callback.message.answer(
            f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    await save_answer(callback.from_user.id, current_question_index, answer_option, is_correct)

    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        answers = await get_answers_by_user_id(callback.from_user.id)
        if answers:
            await callback.message.answer(answers)
        else:
            await callback.message.answer("Ответы не найдены")


async def save_answer(user_id, question_index, selected_option, is_correct):
    async with aiosqlite.connect('quiz_bot.db') as db:
        await db.execute(
            '''INSERT INTO all_answers (user_id, question_index, selected_option, is_correct) VALUES (?, ?, ?, ?)''',
            (user_id, question_index, selected_option, is_correct))
        await db.commit()


async def get_answers_by_user_id(user_id):
    async with aiosqlite.connect('quiz_bot.db') as db:
        cursor = await db.execute(
            f"SELECT question_index, selected_option, is_correct FROM all_answers WHERE user_id = {user_id}")
        rows = await cursor.fetchall()
        if rows:
            answers = []
            correct_answers = 0
            for row in rows:
                question_index, selected_option, is_correct = row
                answer = f"Вопрос №{question_index + 1}\n"
                answer += f"Выбранный вариант: {selected_option}\n"
                answer += "Правильный ответ" if is_correct else "Неправильный ответ"
                answers.append(answer)
                if is_correct:
                    correct_answers += 1
            result = "\n\n".join(answers)
            result += f"\n\nПравильных ответов: {correct_answers} из {len(rows)}"
            return result
        else:
            return None


async def get_quiz_stats():
    async with aiosqlite.connect('quiz_bot.db') as db:
        # Получаем количество уникальных пользователей
        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM all_answers")
        row = await cursor.fetchone()
        total_users = row[0]

        # Получаем общее количество ответов
        cursor = await db.execute("SELECT COUNT(*) FROM all_answers")
        row = await cursor.fetchone()
        total_answers = row[0]

        # Получаем количество правильных ответов
        cursor = await db.execute("SELECT COUNT(*) FROM all_answers WHERE is_correct = 1")
        row = await cursor.fetchone()
        correct_answers = row[0]

        # Вычисляем процент правильных ответов
        if total_answers > 0:
            correct_answers_percentage = (correct_answers / total_answers) * 100
        else:
            correct_answers_percentage = 0

        stats = f"Статистика квиза:\n\n"
        stats += f"Количество участников: {total_users}\n"
        stats += f"Всего ответов: {total_answers}\n"
        stats += f"Правильных ответов: {correct_answers}\n"
        stats += f"Процент правильных ответов: {correct_answers_percentage:.2f}%"

        return stats
