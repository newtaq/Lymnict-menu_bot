import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, Router, filters, types, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.types.keyboard_button import KeyboardButton
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage

import asyncio 
import datetime

from config import BOT_TOKEN
from jsondb import orgsdb, usersdb, shopdb
from sqlshop import shoptable
import os 
from excel_opener import excel2dict


bot = Bot(BOT_TOKEN)
dp = Dispatcher() 
router = Router()


@dp.message(filters.CommandStart())
async def start(message: types.Message):
    await bot.send_message(message.chat.id, "Здравствуйте! Я бот-помощник получения питания в данном заведении. Я могу рассказать о работе наших сервисов и помочь вам выбрать еду для приёма пищи.")
    await asyncio.sleep(1)
    await bot.send_message(message.chat.id, "/help - получить руководство")
    await asyncio.sleep(1)
    
    user_id = f"{message.from_user.id}"
    data = usersdb.data 
    
    if not user_id in data:
        data[user_id] = []
        usersdb.data = data 
        
    await menu(message)
    
@dp.message(filters.Command("help"))
async def help(message: types.Message):
    await bot.send_message(message.chat.id, """1. Если вы являетесь администратором/управляющим предприятия, то выберете "Создать группу", и далее следуете указаниям бота: напишите название вашего предприятия, выберете среди пунктов пункт с названием вашего предприятия. Потом выберете настройки (вариант с шестерёнкой), затем выберете вариант со стрелочкой. Там будет 4 варианта: список участников (вы сможете посмотреть список сотрудников вашего предприятия), добавить меню (для этого нужно будет прислать файл с расширением xlsx (*.xlsx)), выйти из группы (если вы больше не являетесь управляющим предприятия) и удалить группу (если предприятие прекратило своё существование)
2. Если вы являетесь сотрудником предприятия, то выберете "Добавить группу" и следуете указаниям бота: выберете название предприятия, нажмите на "меню" (со значком тележкой), где вы сможете выбрать себе еду, и добавьте товары в корзину, оформив заказ""")

    await asyncio.sleep(2)
    await message.reply("/menu для возвращения в меню")

@dp.message(filters.Command("menu"))
async def menu(message: types.Message):
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Добавить группу", callback_data=f"btn_add_org")

    data = usersdb() 
    user_id = f"{message.from_user.id}"

    shopdb_data = shopdb.data
    shopdb_data[user_id] = []
    shopdb.data = shopdb_data

    if user_id in data:
        for org in data[user_id]:
            kbuilder.button(text=f"{org}", callback_data=f"btn_org_{org}__0")
    
        data_len = len(data[user_id])
        kbuilder.adjust(1, *[5 for _ in range(data_len//5)], data_len % 5 + 1)
    kbuilder.row(InlineKeyboardButton(text="Создать группу", callback_data=f"btn_create_org"))
    await bot.send_message(message.chat.id, f"""\
Вот основное меню (/menu):
/start - перезагрузить бота
/help - получить помощь по боту
/addgroup - добавить группу
/newgroup - создать группу""", reply_markup=kbuilder.as_markup())

@dp.callback_query(lambda query: query.data == "menu")
async def menu_query(query: types.CallbackQuery):
    await menu(query.message.reply_to_message)

@dp.callback_query(lambda query: query.data.startswith("btn_org_"))
async def btn_org(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, page = query.data[8:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    categories = list(orgsdb.data[org_name]["menu"].keys())
    
    len_categories = len(categories) / 10
    int_len_categories = int(len_categories)
    if page < 0:
        page += int_len_categories + 1 if len_categories > 1 else 0 
    elif page > int_len_categories:
        page -= int_len_categories + 1 if len_categories > 1 else 0
    
    window = categories[(page)*10:(page+1)*10]
        
    for category in window:
        kbuilder.button(text=category, callback_data=f"btn_orgcategory_{org_name}__{category}__0")
    
    len_window = len(window)
        
    if len_categories > 1:
        kbuilder.button(text="◀️", callback_data=f"btn_org_{org_name}__{page-1}")
    kbuilder.add(InlineKeyboardButton(text="🛒", callback_data=f"btn_orgshopper_{org_name}"), 
                InlineKeyboardButton(text="⚙️", callback_data=f"btn_orgsettings_{org_name}"))
    if len_categories > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_org_{org_name}__{page+1}")
    
    if len_window % 2:
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 1, 4)
    else: 
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 4)

    if query.message.text == f"Меню для {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"Меню для {org_name}:", reply_markup=kbuilder.as_markup())
        

@dp.callback_query(lambda query: query.data.startswith("btn_orgsettings_"))
async def btn_org_settings(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name = query.data[16:]
    user_id = f"{query.from_user.id}"
        
    data = orgsdb.data 
    
    kbulder = InlineKeyboardBuilder()
    
    if user_id in data[org_name]["admins"]:
        kbulder.button(text="Список участников", callback_data=f"btn_orgmembers_{org_name}__0")
        kbulder.button(text="Добавить меню", callback_data=f"btn_orgadd_menu_{org_name}")
        kbulder.button(text="Удалить группу", callback_data=f"btn_orgdelete_{org_name}")
        kbulder.adjust(1, 1, 1)
    if user_id in data[org_name]["members"]:
        kbulder.button(text="Выйти из группы", callback_data=f"btn_orgleave_{org_name}")        
    
    await bot.send_message(query.message.chat.id, f"Настройки {org_name}:", reply_markup=kbulder.as_markup())        



@dp.callback_query(lambda query: query.data.startswith("btn_orgleave_"))
async def btn_orgleave(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    org_name = query.data[13:]
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Да", callback_data=f"btn_orgleave_true_{org_name}")
    await bot.send_message(query.message.chat.id, "Вы уверены что хотите покинуть эту группу?", reply_markup=kbuilder.as_markup())

   
@dp.callback_query(lambda query: query.data.startswith("btn_orgdelete_"))
async def btn_orgleave(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    org_name = query.data[14:]
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Да", callback_data=f"btn_orgleave_true_{org_name}")
    await bot.send_message(query.message.chat.id, "Вы уверены что хотите удалить эту группу?", reply_markup=kbuilder.as_markup())
    
    
@router.message(filters.Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Отменено",
        reply_markup=ReplyKeyboardRemove(),
    )
    await menu(message)
    
# region btn_orgadd_menu_form
class ExcelForm(StatesGroup):
    excel_file = State()
    
@router.callback_query(lambda query: query.data.startswith("btn_orgadd_menu_"))
async def btn_orgadd_menu(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    org_name = query.data[16:]
    await state.update_data(org_name=org_name)
    await state.set_state(ExcelForm.excel_file)
    await bot.send_message(query.message.chat.id, f"Пришлите *.xlsx файл для {org_name}:\nКоманда /cancel для отмены")
    
@router.message(ExcelForm.excel_file)    
async def btn_orgadd_menu_message(message: types.Message, state: FSMContext):
    org_name = (await state.get_data())["org_name"]
    await state.clear() 
    excel_file: types.Document = message.document
    logging.warning(org_name)
    user_id = f"{message.from_user}"
    orgsdb_data = orgsdb.data 
    
    
    file_path = r"files/" + excel_file.file_name
    await bot.download(excel_file, file_path)
    menu_json = excel2dict(file_path)
    os.remove(file_path)
    
    orgsdb_data[org_name]["menu"] = menu_json
    orgsdb.data = orgsdb_data
    
                    
    await menu(message)
# endregion
            
@dp.callback_query(lambda query: query.data.startswith("btn_orgmembers_"))
async def btn_orgmembers(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, page = query.data[15:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    items = orgsdb.data[org_name]["members"]
    
    len_items = len(items) / 10
    int_len_items = int(len_items)
    if page < 0:
        page += int_len_items + 1 if len_items > 0 else 0
    elif page > int_len_items:
        page -= int_len_items + 1 if len_items > 0 else 0

    window = items[(page)*10:(page+1)*10]
        
    for id, item in enumerate(window):
        kbuilder.button(text=item, callback_data=f"btn_orgmember_{org_name}__{id}")
    
    len_window = len(window)
    kbuilder.adjust(*[2 for _ in range(len_window // 2)], len_window % 2 + 1)
    
    if len_items > 1:       
        kbuilder.row(InlineKeyboardButton(text="◀️", callback_data=f"btn_orgmembers_{org_name}__{page-1}"))
    kbuilder.button(text="↩️", callback_data=f"btn_orgsettings_{org_name}")
    if len_items > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_orgmembers_{org_name}__{page+1}")            

        
    if query.message.text == f"Настройки {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"Настройки {org_name}:", reply_markup=kbuilder.as_markup())        
        
@dp.callback_query(lambda query: query.data.startswith("btn_orgcategory_"))
async def btn_org(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    
    org_name, category, page = query.data[16:].split("__")
    
    page = int(page)    
    
    kbuilder = InlineKeyboardBuilder()

    items = orgsdb.data[org_name]["menu"][category]
    
    len_items = len(items) / 10
    int_len_items = int(len_items)
    if page < 0:
        page += int_len_items + 1 if len_items > 0 else 0
    elif page > int_len_items:
        page -= int_len_items + 1 if len_items > 0 else 0

    window = items[(page)*10:(page+1)*10]
        
    for id, item in enumerate(window):
        kbuilder.button(text=item, callback_data=f"btn_orgitem_{org_name}__{category}__{id+page}")
    
    len_window = len(window)
    
    if len_items > 1:       
        kbuilder.button(text="◀️", callback_data=f"btn_orgcategory_{org_name}__{category}__{page-1}")
    kbuilder.add(InlineKeyboardButton(text="🛒", callback_data=f"btn_orgshopper_{org_name}"), 
                InlineKeyboardButton(text="↩️", callback_data=f"btn_org_{org_name}__0"))
    if len_items > 1:
        kbuilder.button(text="▶️", callback_data=f"btn_orgcategory_{org_name}__{category}__{page+1}")            

    if len_window % 2:
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 1, 4)
    else: 
        kbuilder.adjust(*[2 for _ in range(len_window // 2)], 4)
        
    if query.message.text == f"{category}:" or query.message.text == f"Меню для {org_name}:":
        await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id, reply_markup=kbuilder.as_markup())
    else:
        await bot.send_message(query.message.chat.id, f"{category}:", reply_markup=kbuilder.as_markup())


@dp.callback_query(lambda query: query.data.startswith("btn_orgitem_"))
async def btn_orgitem(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    org_name, category, id = query.data[12:].split("__")
    
    shopdb_data = shopdb.data
    shopdb_data[f"{query.message.chat.id}"] += [orgsdb.data[org_name]["menu"][category][int(id)]]
    shopdb.data = shopdb_data
    
    
@dp.callback_query(lambda query: query.data.startswith("btn_orgshopper_"))
async def btn_orgitem(query: types.CallbackQuery):

    await bot.answer_callback_query(query.id)
    
    kbuilder = InlineKeyboardBuilder()
    kbuilder.button(text="Отправить заказ в столовую", callback_data="btn_endrequest")
    
    items_list = shopdb.data[f'{query.message.chat.id}']
    
    if not items_list:
        await bot.send_message(query.message.chat.id, "Ваша корзина пуста")
        return 
    
    table = shoptable.get_data(query.message.chat.id, f"{datetime.date.today()}")
    if table:
        shoptable.delete_data(query.message.chat.id, f"{datetime.date.today()}")
    shoptable.insert_data(query.message.chat.id, f"{datetime.date.today()}", items_list)

    await bot.send_message(query.message.chat.id, f"Ваша корзина: {', '.join(items_list)}", reply_markup=kbuilder.as_markup())
    
@dp.callback_query(lambda query: query.data == "btn_endrequest")
async def btn_orgitem(query: types.CallbackQuery):

    await bot.answer_callback_query(query.id)    

    await bot.send_message(query.message.chat.id, text="Заказ отправлен в столовую. Корзина очищена.")

    await bot.send_message(query.message.chat.id, "/menu для вызова меню")
    
    
# region btn_create_org_form
class CreateForm(StatesGroup):
    org_name = State()

@router.callback_query(lambda query: query.data == "btn_create_org")
async def btn_create_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(CreateForm.org_name)
    await bot.send_message(query.message.chat.id, "Введите название организации:\nКоманда /cancel для отмены")

    
@router.message(CreateForm.org_name)    
async def btn_create_org_message(message: types.Message, state: FSMContext):
    org_name = message.text
    await state.clear() 
    user_id = f"{message.from_user.id}"
    
    
    usersdbdata = usersdb.data

    if org_name in orgsdb.data:
        await message.reply("Похоже группа с таким названием уже существует")
    else:
        usersdbdata[user_id] += [org_name] 
        usersdb.data = usersdbdata
        orgsdb.data |= {org_name: {"admins": [user_id], "members": [user_id], "menu": {}}}
        await message.reply("Организация успешно создана!")
        
    await menu(message)
# endregion 

# region btn_add_org_form
class AddFrom(StatesGroup):
    org_name = State()

@router.callback_query(lambda query: query.data == "btn_add_org")
async def btn_add_org(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)
    await state.set_state(AddFrom.org_name)
    await bot.send_message(query.message.chat.id, "Введите название организации:\nКомманда /cancel для отмены")
    
@router.message(AddFrom.org_name)    
async def btn_add_org_message(message: types.Message, state: FSMContext):
    org_name = message.text
    await state.clear() 
    user_id = f"{message.from_user.id}"
    db = orgsdb.data
    
    kbuilder = InlineKeyboardBuilder()
    
    if org_name in db:
        
        if user_id in db[org_name]["members"]:
            await message.reply("Вы и так в этой группе")
            await menu(message)
            return
        
        await message.reply("Заявка в группу отправлена!")
        
        kbuilder.button(text="Принять", callback_data=f"btn_add_org_application_true_{org_name}__{message.from_user.id}")
        kbuilder.button(text="Отклонить", callback_data=f"btn_add_org_application_false_{org_name}__{message.from_user.id}")
        
        
        tasks = []
        for admin in db[org_name]["admins"]:
            tasks.append(bot.send_message(int(admin), f"Новая заявка в {org_name} от [{message.from_user.full_name}](t.me//{message.from_user.username})", 
                                          parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True, reply_markup=kbuilder.as_markup()))
        asyncio.gather(*tasks)
        
    else: 
        kbuilder.button(text="Попробовать еще раз", callback_data="btn_add_org")
        kbuilder.row(InlineKeyboardButton(text="Создать группу", callback_data="btn_create_org"), InlineKeyboardButton(text="Меню", callback_data="menu"))
        await message.reply("Похоже такой группы не существует")
    
    await menu(message)    
    
@dp.callback_query(lambda query: query.data.startswith("btn_add_org_application_true_"))
async def btn_create_org_application_true(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id)
    org_name, user_id = query.data[29:].split("__")
    await bot.send_message(int(user_id), f"Ваша заявка в {org_name} была одобрена")
    
    orgsdb_data = orgsdb.data 
    orgsdb_data[org_name]["members"] += [user_id]
    orgsdb.data = orgsdb_data
    
    usersdb_data = usersdb.data 
    usersdb_data[user_id] += [org_name]
    usersdb.data = usersdb_data
    
    await bot.send_message(user_id, "/menu для вызова меню")
    await bot.send_message(query.message.chat.id, "/menu для вызова меню")
    
    
@dp.callback_query(lambda query: query.data.startswith("btn_add_org_application_false_"))
async def btn_create_org_application_true(query: types.CallbackQuery):
    await bot.answer_callback_query(query.id)
    await bot.edit_message_reply_markup(query.message.chat.id, query.message.message_id, query.inline_message_id)
    org_name, user_id = query.data[30:].split("__")
    await bot.send_message(int(user_id), f"Ваша заявка в {org_name} была отклонена")
    
    await bot.send_message(user_id, "/menu для вызова меню")
    await bot.send_message(query.message.chat.id, "/menu для вызова меню")
# endregion 


async def main() -> None:
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())