import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    CallbackContext, ConversationHandler, CallbackQueryHandler
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

USER_PROFILES_FILE = 'user_profiles.json'
waiting_users = []
user_connections = {}
AGE, GENDER = range(2)
user_data = {}

def load_user_profiles():
    if not os.path.exists(USER_PROFILES_FILE):
        save_user_profiles({})
        return {}
    
    try:
        with open(USER_PROFILES_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        save_user_profiles({})
        return {}

def save_user_profiles(profiles):
    with open(USER_PROFILES_FILE, 'w') as f:
        json.dump(profiles, f)

async def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    user_profiles = load_user_profiles()

    keyboard = [
        [InlineKeyboardButton("Start Chat", callback_data="choose_search_mode")],
        [InlineKeyboardButton("View Profile", callback_data="view_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if str(user_id) not in user_profiles:
        user_data[user_id] = {}
        await ask_age(update)
        return AGE

    await update.effective_message.reply_text("Welcome back!", reply_markup=reply_markup)
    return ConversationHandler.END

async def ask_age(update: Update) -> int:
    keyboard = [
        [InlineKeyboardButton("16~18", callback_data="age_16_18"), InlineKeyboardButton("19~21", callback_data="age_19_21")],
        [InlineKeyboardButton("22~24", callback_data="age_22_24"), InlineKeyboardButton("25~27", callback_data="age_25_27")],
        [InlineKeyboardButton("28~30", callback_data="age_28_30"), InlineKeyboardButton("30+", callback_data="age_30_plus")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select your age:", reply_markup=reply_markup)
    return AGE

async def ask_gender(update: Update) -> int:
    keyboard = [
        [InlineKeyboardButton("Male", callback_data="gender_male")],
        [InlineKeyboardButton("Female", callback_data="gender_female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Please select your gender:", reply_markup=reply_markup)
    
    return GENDER

async def age(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    data_parts = query.data.split("_")
    user_data[user_id]['age'] = f"{data_parts[1]}~{data_parts[2]}" if len(data_parts) == 3 else data_parts[1]

    await ask_gender(update)
    return GENDER

async def gender(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    user_data[user_id]['gender'] = query.data.split("_")[1]
    
    user_profiles = load_user_profiles()
    user_profiles[str(user_id)] = user_data[user_id]
    save_user_profiles(user_profiles)
    
    await query.answer()
    await start(update, context)
    return ConversationHandler.END

async def update_age_message(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("16~18", callback_data="age_16_18"), InlineKeyboardButton("19~21", callback_data="age_19_21")],
        [InlineKeyboardButton("22~24", callback_data="age_22_24"), InlineKeyboardButton("25~27", callback_data="age_25_27")],
        [InlineKeyboardButton("28~30", callback_data="age_28_30"), InlineKeyboardButton("30+", callback_data="age_30_plus")],
        [InlineKeyboardButton("Back", callback_data="update_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Select your age range:", reply_markup=reply_markup)
    return AGE

async def update_gender_message(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Male", callback_data="gender_male")],
        [InlineKeyboardButton("Female", callback_data="gender_female")],
        [InlineKeyboardButton("Back", callback_data="update_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Select your gender:", reply_markup=reply_markup)
    return GENDER

async def update_profile(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Update Age", callback_data="update_age")],
        [InlineKeyboardButton("Update Gender", callback_data="update_gender")],
        [InlineKeyboardButton("Back", callback_data="view_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Choose what to update:", reply_markup=reply_markup)
    return ConversationHandler.END

async def choose_search_mode(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔀 Random", callback_data="search_random")],
        [InlineKeyboardButton("⚤ Opposite Gender", callback_data="search_opposite")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Select your search mode:", reply_markup=reply_markup)

async def relay_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in user_connections:
        partner_id = user_connections[user_id]
        await context.bot.send_message(partner_id, update.message.text)

async def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in user_connections:
        partner_id = user_connections.pop(user_id)
        user_connections.pop(partner_id, None)
        await context.bot.send_message(partner_id, "Your chat partner has left the chat. You have been disconnected.")
        await update.message.reply_text("Chat ended. You have been disconnected.")
    else:
        await update.message.reply_text("You are not in a chat.")

async def start_chat(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    search_mode = query.data  # "search_random" or "search_opposite"

    user_profiles = load_user_profiles()
    if str(user_id) not in user_profiles:
        await query.answer("You need to set up your profile first!", show_alert=True)
        return

    user_profile = user_profiles[str(user_id)]
    user_gender = user_profile["gender"]

    await query.answer()
    await query.edit_message_text("Searching for a match... Please wait.")
    
    global waiting_users

    if search_mode == "search_random":
        for waiting_id in waiting_users:
            if waiting_id != user_id:
                waiting_users.remove(waiting_id)
                user_connections[user_id] = waiting_id
                user_connections[waiting_id] = user_id
                await context.bot.send_message(user_id, f"Connected! 🎉\nYour partner's age range: {user_profiles[str(waiting_id)]['age']}\nGender: {user_profiles[str(waiting_id)]['gender']}\nType /stop to end the chat.")
                await context.bot.send_message(waiting_id, f"Connected! 🎉\nYour partner's age range: {user_profiles[str(user_id)]['age']}\nGender: {user_profiles[str(user_id)]['gender']}\nType /stop to end the chat.")
                return
    else:  # "search_opposite"
        for waiting_id in waiting_users:
            if waiting_id != user_id and user_profiles[str(waiting_id)]["gender"] != user_gender:
                waiting_users.remove(waiting_id)
                user_connections[user_id] = waiting_id
                user_connections[waiting_id] = user_id
                await context.bot.send_message(user_id, f"Connected! 🎉\nYour partner's age range: {user_profiles[str(waiting_id)]['age']}\nGender: {user_profiles[str(waiting_id)]['gender']}\nType /stop to end the chat.")
                await context.bot.send_message(waiting_id, f"Connected! 🎉\nYour partner's age range: {user_profiles[str(user_id)]['age']}\nGender: {user_profiles[str(user_id)]['gender']}\nType /stop to end the chat.")
                return
    
    waiting_users.append(user_id)
            
async def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in user_connections:
        partner_id = user_connections.pop(user_id)
        user_connections.pop(partner_id, None)
        await context.bot.send_message(partner_id, "Your chat partner has left the chat.")
    await update.message.reply_text("Chat ended.")

async def view_profile(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    user_profiles = load_user_profiles()

    keyboard = [
        [InlineKeyboardButton("Update Profile", callback_data="update_profile")],
        [InlineKeyboardButton("Back", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if str(user_id) in user_profiles:
        profile = user_profiles[str(user_id)]
        profile_text = f"👤 **Your Profile:**\n\n"
        profile_text += f"📅 Age: {profile.get('age', 'Not set')}\n"
        profile_text += f"⚧ Gender: {profile.get('gender', 'Not set')}\n"
    else:
        profile_text = "No profile found. Please update your profile."

    await query.answer()
    await query.edit_message_text(profile_text, parse_mode="Markdown", reply_markup=reply_markup)

def main():
    application = Application.builder().token("7662725179:AAGBe1MQ8q_8-7bpdl30lXiX_GHOxsCj5TI").build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [CallbackQueryHandler(age)],
            GENDER: [CallbackQueryHandler(gender)],
        },
        
        fallbacks=[],
    )

    application.add_handler(conversation_handler)
    application.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    application.add_handler(CallbackQueryHandler(start_chat, pattern="^start_chat$"))
    application.add_handler(CallbackQueryHandler(choose_search_mode, pattern="^choose_search_mode$"))
    application.add_handler(CallbackQueryHandler(start_chat, pattern="^(search_random|search_opposite)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))
    application.add_handler(CallbackQueryHandler(update_profile, pattern="^update_profile$"))
    application.add_handler(CallbackQueryHandler(update_age_message, pattern="^update_age$"))
    application.add_handler(CallbackQueryHandler(update_gender_message, pattern="^update_gender$"))
    application.add_handler(CallbackQueryHandler(view_profile, pattern="^view_profile$"))
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling()

if __name__ == '__main__':
    main()