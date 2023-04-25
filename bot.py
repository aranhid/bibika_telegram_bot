import re
import logging
import random
import textwrap

import pandas as pd
from aiogram import Bot, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.types import Message

from aiogram.utils.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from secret import TOKEN

logging.basicConfig(level=logging.INFO)

cars_df = pd.read_csv('sub_hon_toy.csv')

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage = storage)

class UserState(StatesGroup):
    manufacturer = State()
    model = State()
    generation_country = State()
    generation_name = State()
    generation_date_start = State()
    generation_date_end = State()
    generation_body = State()
    engine_volume = State()
    engine_hp = State()
    fuel_type = State()
    transmission_type = State()
    drive = State()

    return_answer = State()
    goodby = State()

# возможные ответы пользователя
# positive_vibes = ["хорош", "супер", "класс", "прекрасн"]
# negative_vibes = ["плох", "не очень", "так себе"]

# возможные стикеры на ответ пользователю
stickers_positive = [
    "CAACAgIAAxkBAAEIt5xkR4HL9QTpWYk6iQ6AgbxEPnDLqQACDioAAt1nQUpP0mg9dWgrSi8E",
]

stickers_neutral = [
    "CAACAgIAAxkBAAEIt55kR4IAAcbO6lwPrGuCX0mlaVpFx_gAAkkpAAJtFTlKlfIEKdOpS4kvBA",
]

stickers_negative = [
    "CAACAgIAAxkBAAEIt6BkR4INVP1MCmwi5Ktjv-elQNr_ewACbyYAAmD6OEqSFjt0TYhakC8E",
]

# возможные ответы бота
negative_messages = [
    "Очень жаль, что вам не понравилось.",
    "За что вы так?"
]
positive_messages = [
    "Не за что!",
    "Всегда рад помочь!",
    "Пожалуйста, всегда рад помочь! Обращайтесь ещё!"
]
neutral_messages  = [
     "Каво?",
     "Моя твоя не понимать. Напиши на машинном.",
     "Ко мне ещё не подключили интерфейс ChatGPT, поэтому я не умею отвечать на такие сообщения. Напиши просьбу правильно.",
]

async def get_key_by_state(state: FSMContext):
    temp = await state.get_state()
    return temp.split(':')[-1]

async def get_next_state(state: FSMContext):
    states = [str(state.state) for state in UserState.states]
    print(states)
    current_state = await state.get_state()
    idx = states.index(current_state)
    next_state = states[idx+1]
    return next_state.split(':')[-1]

# возвращает список вариантов ответа
def get_variants(df: pd.DataFrame, key):
    variants = list(df[key].unique())

    variants = [str(variant) for variant in variants]
    variants = sorted(variants)
    # variants.append('Не важно')
    variants.insert(0, 'Не важно')
    variants.insert(0, 'Стоп')
    return variants

def get_keyboard(df, key):
    keyboard = ReplyKeyboardMarkup()
    variants = get_variants(df, key)

    for variant in variants:
        keyboard.add(
            KeyboardButton(variant)
        )

    return keyboard

def get_menu_keyboard():
    keyboard = ReplyKeyboardMarkup()

    keyboard.add(
        KeyboardButton("Меню")
    )

    return keyboard

def check_answer(answer, key):
    if answer not in get_variants(cars_df, key):
        return False
    return True

async def get_cars(state: FSMContext):
    global cars_df

    df = cars_df.copy()
    user_data = await state.get_data()
    user_data.pop("return_answer", None)
    print(user_data)
    for key, value in user_data.items():
        if value:
            if ">" in value or "<" in value:
                print(f'{key} {value}')
                df = df.query(f'{key} {value}')
            elif value.replace('.', '', 1).isdigit():
                # float comparision
                df = df.query(f'{key} == {value}')
            elif value == 'Не важно':
                pass
            else:
                df = df[df[key] == value]

    return df

async def my_message_handler(message, state: FSMContext, next_message):
    current_key = await get_key_by_state(state)
    next_key = await get_next_state(state)
    if message.text not in get_variants(cars_df, current_key):
        df = await get_cars(state)
        keyboard = get_keyboard(df, current_key)
        await message.answer_sticker(random.choice(stickers_neutral))
        await message.answer(random.choice(neutral_messages))
        await message.answer("Напиши правильный ответ.", reply_markup=keyboard)
        return
    elif message.text == 'Стоп':
            await goodby(message, state)
            return
    await state.update_data({current_key: message.text})
    if next_key != "return_answer":
        df = await get_cars(state)
        keyboard = get_keyboard(df, next_key)
        await message.answer(next_message, reply_markup=keyboard)
        await UserState.next()
    # else:
    #     df = await get_cars(state)
    #     df.reset_index(drop=True, inplace=True)
    #     await UserState.return_answer.set()
    #     await state.update_data(return_answer = df)

async def print_answer(message: Message, state: FSMContext):
    await message.answer("Вот такой вариант:")

    user_data = await state.get_data()

    df = user_data["return_answer"]
    df.reset_index(drop=True, inplace=True)
    data = df.loc[0].to_dict()
    print(data)
    data['feature'] = data['feature'] if str(data['feature']) != 'nan' else ""
    print(data)
    df.drop(0, inplace = True)
    df.reset_index(drop=True, inplace=True)
    await state.update_data(return_answer = df)


    text = textwrap.dedent(f"""
    ***Марка:*** {re.escape(data["manufacturer"])}
    ***Модель:*** {re.escape(data["model"])}
    ***Рынок:*** {re.escape(data["generation_country"])}
    ***Поколение:*** {re.escape(data["generation_name"])}
    ***Старт производства:*** {re.escape(str(data["generation_date_start"]))}
    ***Конец производства:*** {re.escape(str(data["generation_date_end"]))}
    ***Тип кузова:*** {re.escape(data["generation_body"])}
    ***Объём двигателя:*** {re.escape(str(data["engine_volume"]))}
    ***Мощность двигателя:*** {re.escape(str(data["engine_hp"]))}
    ***Тип топлива:*** {re.escape(data["fuel_type"])}
    ***Тип трансмиссии:*** {re.escape(data["transmission_type"])}
    ***Привод:*** {re.escape(data["drive"])}
    {f"***Особенности:*** {re.escape(data['feature'])}" if len(data["feature"]) else ""}
    """)


    keyboard = InlineKeyboardMarkup()
    key = InlineKeyboardButton(
        text="Подробне на drom.ru",
        url=data['generation_url']
    )
    keyboard.add(key)

    await message.answer_photo(data["generation_img_url"])
    await message.answer(text=text, parse_mode='MarkdownV2', reply_markup=keyboard)
    # await message.answer(text="Ссылка на drom.ru", reply_markup=key)

@dp.message_handler(commands=['start', 'help'])
async def start_command(message: Message):
    await message.answer(textwrap.dedent(f"""
    Привет! Я - Бибика, и я бот-автоподборщик! Я помогу тебе подобрать автомобиль по заданным тобой параметрам.
    Я знаю такие команды:
    /pick_car - выбрать автомобиль по параметрам.
    /random_car - покажу тебе рандомный автомобиль.
    /help - верну данное сообщение.
    """), reply_markup=get_menu_keyboard())

    # Отправляем приветственный гиф пользователю
    # await bot.send_animation(message.chat.id, 'https://i.pinimg.com/originals/7d/9b/1d/7d9b1d662b28cd365b33a01a3d0288e1.gif')
    await message.answer_sticker(random.choice(stickers_positive))

@dp.message_handler(commands="random_car")
async def pick_random_car(message: Message, state: FSMContext):
    await UserState.return_answer.set()
    df = cars_df.copy()
    df = df.sample(frac=1).reset_index(drop=True)
    await state.update_data(return_answer = df)
    await return_answer(message, state)

@dp.message_handler(commands="pick_car")
async def pick_car(message: Message, state: FSMContext):
    await message.answer('Чтобы подобрать тебе автообиль, я буду задавать вопросы, а ты на них должен отвечать.')
    keyboard = get_keyboard(cars_df, 'manufacturer')
    await message.answer('Первый вопрос: Какую марку ищите?', reply_markup=keyboard)
    await UserState.manufacturer.set()

@dp.message_handler(state=UserState.manufacturer)
async def pick_manufacturer(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Какую модель ищите?")

@dp.message_handler(state=UserState.model)
async def pick_model(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Для какого рынка?")

@dp.message_handler(state=UserState.generation_country)
async def pick_market(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Какое поколение?")

@dp.message_handler(state=UserState.generation_name)
async def pick_start_date(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Год начала выпуска?")

@dp.message_handler(state=UserState.generation_date_start)
async def pick_end_date(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Год конца выпуска?")

@dp.message_handler(state=UserState.generation_date_end)
async def pick_model(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Тип кузова?")

@dp.message_handler(state=UserState.generation_body)
async def pick_body(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Объём двигателя?")

@dp.message_handler(state=UserState.engine_volume)
async def pick_model(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Мощность?")

@dp.message_handler(state=UserState.engine_hp)
async def pick_hp(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Тип топлива?")

@dp.message_handler(state=UserState.fuel_type)
async def pick_fuel(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Тип трансмиссии?")

@dp.message_handler(state=UserState.transmission_type)
async def pick_transmission(message: Message, state: FSMContext):
    await my_message_handler(message, state, "Привод?")

@dp.message_handler(state=UserState.drive)
async def pick_drive(message: Message, state: FSMContext):
    await my_message_handler(message, state, "")
    df = await get_cars(state)
    df.reset_index(drop=True, inplace=True)
    await UserState.return_answer.set()
    await state.update_data(return_answer = df)
    await return_answer(message, state)
    # # df = await get_cars(state)

    # await print_answer(message, state)

    # user_data = await state.get_data()
    # df = user_data["return_answer"]

    # if len(df) > 0:
    #     await message.answer("Хотите ещё вариант?")
    # else:
    #     await message.answer("Больше вариантов нету")
    #     await UserState.goodby.set()

@dp.message_handler(state=UserState.return_answer)
async def return_answer(message: Message, state: FSMContext):
    if message.text in ["Нет, спасибо!", "Нет, плохие варианты!"]:
        await goodby(message, state)
        return

    await print_answer(message, state)

    user_data = await state.get_data()
    df = user_data["return_answer"]

    if len(df) > 0:
        keyboard = ReplyKeyboardMarkup()
        keyboard.add(
            KeyboardButton('Да, давай')
        )
        keyboard.add(
            KeyboardButton('Нет, спасибо!')
        )
        keyboard.add(
            KeyboardButton('Нет, плохие варианты!')
        )
        await message.answer("Хотите ещё вариант?", reply_markup=keyboard)
    else:
        keyboard = ReplyKeyboardMarkup()
        keyboard.add(
            KeyboardButton('Спасибо!')
        )
        keyboard.add(
            KeyboardButton('Плохие варианты')
        )
        await message.answer("Больше вариантов нету", reply_markup=keyboard)
        await UserState.goodby.set()

@dp.message_handler(state=UserState.goodby)
async def goodby(message: Message, state: FSMContext):
    if message.text in ['Спасибо!', 'Нет, спасибо!', 'Стоп']:
        await message.answer_sticker(random.choice(stickers_positive))
        await message.answer(random.choice(positive_messages), reply_markup=get_menu_keyboard())
    elif message.text in ['Плохие варианты', 'Нет, плохие варианты!']:
        await message.answer_sticker(random.choice(stickers_negative))
        await message.answer(random.choice(negative_messages), reply_markup=get_menu_keyboard())
    else:
        await message.answer_sticker(random.choice(stickers_neutral))
        await message.answer("Я вас не понял, но будем считать, что вы сказали спасибо.", reply_markup=get_menu_keyboard())
    await state.finish()

@dp.message_handler()
async def just_a_message(message: Message):
    if message.text == "Меню":
        await message.answer(textwrap.dedent(f"""
            Я знаю такие команды:
            /pick_car - выбрать автомобиль по параметрам.
            /random_car - покажу тебе рандомный автомобиль.
            /help - верну данное сообщение.
        """))
    elif message.text == "Ты кто такой?":
        await message.answer("Я – Бибика - Aвтоподборщик! Готов подобрать тебе автомобиль!")
    elif message.text == "Ты глупый бот":
        await message.answer("За что вы так?(")
        await message.answer_sticker(random.choice(stickers_negative))
    else:
        await message.answer(random.choice(neutral_messages))

if __name__ == '__main__':
    executor.start_polling(dp)