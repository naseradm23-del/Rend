import os
import logging
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# الحصول على التوكن من متغير البيئة (مهم لـ Render)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# بيانات المطور
DEVELOPER = "ناصر"

# قاموس لتخزين طلبات المستخدمين
user_requests: Dict[int, Dict] = {}

# التحقق من التوكن
if TOKEN == 'YOUR_BOT_TOKEN_HERE':
    logger.error("❌ لم يتم تعيين توكن البوت! يرجى تعيين متغير البيئة TELEGRAM_BOT_TOKEN")
    print("❌ خطأ: لم يتم تعيين توكن البوت")
    print("📝 على Render: اذهب إلى Dashboard -> Environment -> Add Environment Variable")
    print("🔑 المفتاح: TELEGRAM_BOT_TOKEN")
    print("💎 القيمة: توكن البوت الذي حصلت عليه من @BotFather")
    exit(1)

# دالة البدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = f"🎵 أهلاً {user.first_name}!\n\nأنا بوت البحث عن الأغاني 🎶\n\n" \
                      "✨ **كيفية الاستخدام:**\n" \
                      "1. اكتب 'نصور' متبوعة باسم الأغنية\n" \
                      "   مثال: `نصور أغنية حبيبي`\n" \
                      "2. سأبحث عن الأغنية وأرسلها لك\n\n" \
                      "🚀 **ميزات إضافية:**\n" \
                      "- اضغط على زر '⭐' (نجمة) لتحصل على رسالة ترحيب خاصة\n" \
                      "- البحث السريع والدقيق عن الأغاني\n\n" \
                      f"📱 **المطور:** ﴿{DEVELOPER}﴾\n" \
                      f"🆔 **معرفك:** `{user.id}`"
    
    # إضافة زر للمساعدة
    keyboard = [[InlineKeyboardButton("🆘 المساعدة", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# دالة معالجة النجمة (Stars)
async def handle_star(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    star_message = f"✨ **أهلاً وسهلاً {user.first_name}!** ✨\n\n" \
                   "شكراً لإعجابك بالبوت 🌟\n\n" \
                   "أنا هنا لمساعدتك في العثور على أي أغنية تريدها 🎶\n" \
                   "ما عليك سوى كتابة 'نصور' متبوعة باسم الأغنية\n\n" \
                   "**مثال:** `نصور أغنية الحب`\n\n" \
                   f"📞 **تواصل مع المطور:** ﴿{DEVELOPER}﴾"
    
    await update.message.reply_text(star_message, parse_mode='Markdown')

# دالة البحث عن الأغاني
async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # التحقق من أن الرسالة تبدأ بـ "نصور"
    if not message_text.startswith("نصور"):
        return
    
    # استخراج اسم الأغنية
    song_name = message_text[5:].strip()
    
    if not song_name:
        await update.message.reply_text("⚠️ من فضلك اكتب اسم الأغنية بعد 'نصور'\nمثال: `نصور أغنية الطريق`", parse_mode='Markdown')
        return
    
    # إعلام المستخدم بأن البحث قيد التقدم
    search_message = await update.message.reply_text(f"🔍 **جاري البحث عن:** `{song_name}`\n⏳ يرجى الانتظار...", parse_mode='Markdown')
    
    try:
        # البحث عن الأغنية على YouTube
        search_results = await asyncio.to_thread(search_youtube, song_name)
        
        if not search_results:
            await search_message.edit_text(f"❌ **لم أتمكن من العثور على:** `{song_name}`\nحاول استخدام كلمات أخرى للبحث.", parse_mode='Markdown')
            return
        
        # تخزين النتائج للمستخدم
        user_requests[user_id] = {
            'results': search_results,
            'current_index': 0
        }
        
        # عرض أول نتيجة مع أزرار التنقل
        await send_song_result(update, context, user_id, search_message)
        
    except Exception as e:
        logger.error(f"Error searching for song: {e}")
        await search_message.edit_text("❌ حدث خطأ أثناء البحث. يرجى المحاولة مرة أخرى.")

# دالة البحث على YouTube
def search_youtube(query, max_results=5):
    search_results = []
    
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'format': 'bestaudio/best',
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            if 'entries' in result:
                for entry in result['entries']:
                    if entry:
                        search_results.append({
                            'title': entry.get('title', 'Unknown'),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                            'duration': entry.get('duration', 0),
                            'thumbnail': entry.get('thumbnails', [{}])[0].get('url', '') if entry.get('thumbnails') else '',
                            'channel': entry.get('channel', 'Unknown') or 'Unknown'
                        })
    
    except Exception as e:
        logger.error(f"Error in YouTube search: {e}")
    
    return search_results

# دالة إرسال نتيجة الأغنية
async def send_song_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, message=None):
    if user_id not in user_requests or not user_requests[user_id]['results']:
        return
    
    user_data = user_requests[user_id]
    results = user_data['results']
    current_index = user_data['current_index']
    
    if current_index >= len(results):
        current_index = 0
        user_data['current_index'] = 0
    
    song = results[current_index]
    
    # إنشاء لوحة الأزرار
    keyboard = []
    
    # أزرار التنقل بين النتائج
    if len(results) > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"prev_{user_id}"))
        
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{len(results)}", callback_data="page"))
        
        if current_index < len(results) - 1:
            nav_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"next_{user_id}"))
        
        keyboard.append(nav_buttons)
    
    # أزرار التنزيل والمشاركة
    action_buttons = [
        InlineKeyboardButton("🎵 استمع على YouTube", url=song['url']),
        InlineKeyboardButton("🔗 مشاركة", callback_data=f"share_{user_id}_{current_index}")
    ]
    keyboard.append(action_buttons)
    
    # زر إرسال الأغنية للقروب
    keyboard.append([InlineKeyboardButton("📤 إرسال للقروب", callback_data=f"send_{user_id}_{current_index}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحضير رسالة النتيجة
    duration_str = ""
    if song['duration']:
        minutes = song['duration'] // 60
        seconds = song['duration'] % 60
        duration_str = f"\n⏳ المدة: {minutes}:{seconds:02d}"
    
    caption = f"🎶 **{song['title']}**\n" \
              f"📺 القناة: {song['channel']}{duration_str}\n\n" \
              f"📱 **المطور:** ﴿{DEVELOPER}﴾"
    
    # إرسال النتيجة
    try:
        if song.get('thumbnail'):
            # إذا كان لدينا صورة مصغرة، أرسلها مع النص
            if message:
                await message.delete()
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=song['thumbnail'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # إذا لم توجد صورة مصغرة، أرسل النص فقط
            if message:
                await message.edit_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error sending result: {e}")
        # إذا فشل إرسال الصورة، أرسل النص فقط
        error_caption = f"🎶 **{song['title']}**\n" \
                       f"🔗 [شاهد على YouTube]({song['url']})\n" \
                       f"📺 القناة: {song['channel']}{duration_str}\n\n" \
                       f"📱 **المطور:** ﴿{DEVELOPER}﴾"
        
        if message:
            await message.edit_text(error_caption, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=False)
        else:
            await update.message.reply_text(error_caption, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=False)

# دالة معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await help_command_callback(query, context)
        return
    
    if data.startswith("prev_") or data.startswith("next_"):
        # استخراج معرف المستخدم
        parts = data.split("_")
        if len(parts) < 2:
            return
        
        try:
            target_user_id = int(parts[1])
        except:
            return
        
        # تحديث الفهرس
        if target_user_id in user_requests:
            user_data = user_requests[target_user_id]
            
            if data.startswith("prev_"):
                user_data['current_index'] = max(0, user_data['current_index'] - 1)
            else:  # next
                user_data['current_index'] = min(len(user_data['results']) - 1, user_data['current_index'] + 1)
            
            # إرسال النتيجة المحدثة
            await send_song_result(update, context, target_user_id)
    
    elif data.startswith("send_"):
        # إرسال الأغنية للقروب
        parts = data.split("_")
        if len(parts) < 3:
            return
        
        try:
            target_user_id = int(parts[1])
            song_index = int(parts[2])
        except:
            return
        
        if target_user_id in user_requests:
            results = user_requests[target_user_id]['results']
            if 0 <= song_index < len(results):
                song = results[song_index]
                
                # إنشاء رسالة للمشاركة في القروب
                share_message = f"🎵 **تمت مشاركة أغنية:**\n\n" \
                               f"**{song['title']}**\n" \
                               f"🔗 [استمع على YouTube]({song['url']})\n" \
                               f"📺 القناة: {song['channel']}\n\n" \
                               f"📤 تمت المشاركة بواسطة: {query.from_user.first_name}\n" \
                               f"📱 **المطور:** ﴿{DEVELOPER}﴾"
                
                # إرسال الرسالة في نفس الدردشة (القروب)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=share_message,
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )

# دالة المساعدة (من خلال callback)
async def help_command_callback(query, context):
    help_text = f"🆘 **دليل استخدام البوت:**\n\n" \
                "🔍 **للبحث عن أغنية:**\n" \
                "اكتب 'نصور' متبوعة باسم الأغنية\n" \
                "مثال: `نصور أغنية الحب`\n\n" \
                "⭐ **للترحيب:**\n" \
                "اضغط على أيقونة النجمة (⭐) لتحصل على رسالة ترحيب\n\n" \
                "🎵 **عند ظهور نتائج البحث:**\n" \
                "- استخدم أزرار ◀️ و ▶️ للتنقل بين النتائج\n" \
                "- اضغط على '🎵 استمع على YouTube' لفتح الأغنية\n" \
                "- اضغط على '📤 إرسال للقروب' لمشاركة الأغنية\n\n" \
                f"📞 **المطور:** ﴿{DEVELOPER}﴾\n" \
                "شكراً لاستخدامك البوت! 🎶"
    
    await query.edit_message_text(help_text, parse_mode='Markdown')

# دالة المساعدة (من خلال الأمر)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"🆘 **دليل استخدام البوت:**\n\n" \
                "🔍 **للبحث عن أغنية:**\n" \
                "اكتب 'نصور' متبوعة باسم الأغنية\n" \
                "مثال: `نصور أغنية الحب`\n\n" \
                "⭐ **للترحيب:**\n" \
                "اضغط على أيقونة النجمة (⭐) لتحصل على رسالة ترحيب\n\n" \
                "🎵 **عند ظهور نتائج البحث:**\n" \
                "- استخدم أزرار ◀️ و ▶️ للتنقل بين النتائج\n" \
                "- اضغط على '🎵 استمع على YouTube' لفتح الأغنية\n" \
                "- اضغط على '📤 إرسال للقروب' لمشاركة الأغنية\n\n" \
                f"📞 **المطور:** ﴿{DEVELOPER}﴾\n" \
                "شكراً لاستخدامك البوت! 🎶"
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# دالة للمطور
async def developer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dev_message = f"👨‍💻 **معلومات المطور:**\n\n" \
                  f"**الاسم:** ﴿{DEVELOPER}﴾\n" \
                  "**البوت:** بوت البحث عن الأغاني 🎵\n\n" \
                  "هذا البوت تم برمجته خصيصاً للبحث عن الأغاني\n" \
                  "ومشاركتها في مجموعات التليجرام بسهولة.\n\n" \
                  "✨ **مميزات البوت:**\n" \
                  "- بحث سريع عن الأغاني\n" \
                  "- واجهة مستخدم سهلة\n" \
                  "- إمكانية مشاركة الأغاني في القروب\n" \
                  "- رسائل ترحيب تفاعلية\n\n" \
                  "⚡ **السيرفر:** Render.com\n" \
                  "🕒 **وقت التشغيل:** 24/7\n\n" \
                  "شكراً لاستخدامك البوت! 🎶"
    
    await update.message.reply_text(dev_message, parse_mode='Markdown')

# دالة للحفاظ على البوت نشطاً (لـ Render)
async def keep_alive():
    """دالة للحفاظ على البوت نشطاً"""
    while True:
        logger.info("🟢 البوت يعمل...")
        await asyncio.sleep(300)  # كل 5 دقائق

# دالة البداية
async def start_bot():
    """دالة لبدء تشغيل البوت"""
    print(f"🎵 بدء تشغيل بوت الأغاني... | المطور: {DEVELOPER}")
    print(f"🔑 التوكن: {'****' + TOKEN[-8:] if len(TOKEN) > 8 else 'غير صالح'}")
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("developer", developer))
    application.add_handler(CommandHandler("مطور", developer))
    
    # معالج النجمة (Stars) - يتعامل مع الرسائل التي تحتوي على نجمة
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^⭐|نجمة|star'), handle_star))
    
    # معالج البحث عن الأغاني
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_song))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # بدء البوت
    print("🚀 البوت جاهز للاستخدام!")
    print("📝 أرسل /start إلى البوت للبدء")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # تشغيل دالة الحفاظ على النشاط
    await keep_alive()

# الدالة الرئيسية
def main():
    """الدالة الرئيسية للتشغيل"""
    print("=" * 50)
    print("🎵 بوت تليجرام للبحث عن الأغاني")
    print(f"👨‍💻 المطور: {DEVELOPER}")
    print("⚡ مُهيأ للتشغيل على Render.com")
    print("=" * 50)
    
    # تشغيل البوت
    asyncio.run(start_bot())

if __name__ == '__main__':
    main()