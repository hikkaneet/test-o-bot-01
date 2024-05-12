from aiogram import types, F, Router
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from functions import new_quiz, process_answer, get_quiz_stats

router = Router()


# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик две кнопки
    builder.add(types.KeyboardButton(text="Начать игру"))
    builder.add(types.KeyboardButton(text="Статистика"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


# Хэндлер на команды /quiz
@router.message(F.text == "Начать игру")
@router.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз!")
    # Запускаем новый квиз
    await new_quiz(message)


# Хэндлер для кнопки "Статистика"
@router.message(F.text == "Статистика")
async def show_stats(message: types.Message):
    # Получаем статистику квиза
    stats = await get_quiz_stats()
    # Отправляем статистику в чат
    await message.answer(stats)


@router.callback_query(F.data.startswith("right_answer;"))
async def right_answer(callback: types.CallbackQuery):
    # Получаем вариант ответа, отбрасывая префикс "right_answer;"
    answer_option = callback.data.split(";")[1]

    # Дальнейшая обработка правильного ответа
    await process_answer(callback, is_correct=True, answer_option=answer_option)


@router.callback_query(F.data.startswith("wrong_answer;"))
async def wrong_answer(callback: types.CallbackQuery):
    # Получаем вариант ответа, отбрасывая префикс "wrong_answer;"
    answer_option = callback.data.split(";")[1]

    # Дальнейшая обработка неправильного ответа
    await process_answer(callback, is_correct=False, answer_option=answer_option)
