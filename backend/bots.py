import atexit
import io
import json
import logging
import os
import tempfile
import threading
import time
from collections import defaultdict

import itchat
from itchat.components.login import push_login
from pyqrcode import QRCode
from wxpy import User, Chat, Bot, Messages
from wxpy.api.messages import Registered, MessageConfig
from wxpy.compatible import PY2
from wxpy.utils import enhance_webwx_request, wrap_user_name, enhance_connection

logger = logging.getLogger(__name__)


def bot_command_handler(message):
    if message.text.startswith('🤖️'):
        return

    if message.text == '退出':
        message.reply('🤖️再见👋')
        message.bot.logout()
    else:
        message.reply('🤖️不知道你要干什么呢～')


def bot_func(message):
    logger.info("[%s] %s " % (message.bot.bot_name, message))
    bot = message.bot
    # session = db_session()
    # msg = BotMessage(bot_name=bot.self.name, sender=message.member.name if message.member else message.sender.name,
    #                  chat=message.chat.name, type=message.type, message=message.text,
    #                  url=message.url, created_at=datetime.now())
    # session.add(msg)
    # session.commit()

    if bot.master:
        bot_master_handler(message)
        return
    elif bot.self == message.sender and message.chat in (bot.self, bot.file_helper):
        bot_command_handler(message)
        return

    # articles = message.articles

    if message.type == 'Friends' and bot.auto_accept:
        # 好友申请
        bot.accept_friend(message.card)


def bot_master_handler(message):
    global master_bot
    if message.sender == message.bot.self and message.chat in (message.bot.self, message.bot.file_helper):
        # 只处理自己发给自己的
        if '登录' == message.text:
            bot_login_prepare(message.bot.file_helper)
        elif '确认替换' == message.text:
            if master_bot.to_confirm_replace:
                old_master = master_bot
                to_confirm_replace = old_master.to_confirm_replace
                old_master.to_confirm_replace = None
                set_master_bot(to_confirm_replace)
                old_master.master = False
                message.reply('🤖️替换成功，您已转成普通账户')
                add_running_bot(old_master)
            else:
                message.reply('🤖️替换失败')
        else:
            bot_command_handler(message)


def bot_login_prepare(target, count=0):
    bot = AsyncBot()
    qr_img = bot.get_qr()

    target.send_msg('🤖️扫描二维码登录')

    tmp = '/tmp/%s.png' % time.time()
    with open(tmp, 'wb') as f:
        f.write(qr_img.getvalue())

    target.send_image(tmp)

    maintain_thread = threading.Thread(target=bot_login_watch, name='%s login watcher ' % target,
                                       args=(target, bot, count))
    maintain_thread.setDaemon(True)
    maintain_thread.start()


def bot_login_watch(user, bot, count):
    begin = time.time()
    while True:
        status = bot.check_login()
        if status == '200':
            # 登录成功
            bot.post_login()
            logger.info("[%s] %s" % (bot.bot_name, '登录成功'))
            user.send_msg('🤖️登录成功')
            return
        elif status == '408':
            if count < 3:
                bot_login_prepare(user, count + 1)
            return
        elif time.time() - begin > 300:
            user.send_msg('🤖️登录失败')
            bot.logout()
            return
        time.sleep(1)


def add_running_bot(bot):
    global running_bots

    if bot.self.name in running_bots:
        b = running_bots.pop(bot.self.name)
        b.logout()

    running_bots[bot.self.name] = bot


def load_bots():
    os.makedirs('data/bots', exist_ok=True)
    files = os.listdir('data/bots')
    print('Loading bots')
    for file in files:
        if file.endswith(".pkl"):
            bot = AsyncBot()
            status = bot.core.load_login_status('data/bots/' + file, exitCallback=bot.bot_logout)
            if bool(status):
                bot.core.hotReloadDir = 'data/bots/' + file
                bot.post_login(dump=False)

    print("Running bots: %s" % running_bots)


class AsyncBot(Bot):
    @property
    def bot_name(self):
        return self.self.name if hasattr(self, 'self') else '[匿名]'

    def __str__(self):
        return '<Bot: %s>' % (self.self.name if self.self else '[未登录]')

    def __init__(self):
        self.master = False
        self.core = itchat.Core()
        itchat.instanceList.append(self)

        # 用于 "synccheck" 请求的 "_" 参数，每次请求时 + 1
        self._sync_check_iterations = int(time.time() * 1000)

        self.auto_mark_as_read = False
        enhance_connection(self.core.s)

        self.cache_path = None

        self.messages = Messages()
        self.registered = Registered(self)

        self.isLogging = True
        self.puid_map = None
        self.auto_send = False

        self.is_listening = False
        self.listening_thread = None

        self.crawler_articles = True
        self.app_id = None
        self.auto_accept = False

        if PY2:
            from wxpy.compatible.utils import TemporaryDirectory
            self.temp_dir = TemporaryDirectory(prefix='wxpy_')
        else:
            self.temp_dir = tempfile.TemporaryDirectory(prefix='wxpy_')

        atexit.register(self._cleanup)

    def get_qr(self):
        push_login(self.core)
        self.core.get_QRuuid()
        uuid = self.core.uuid
        qrStorage = io.BytesIO()
        qrCode = QRCode('https://login.weixin.qq.com/l/' + uuid)
        qrCode.png(qrStorage, scale=10)
        return qrStorage

    def check_login(self):
        return self.core.check_login()

    def self_msg(self, msg):
        if self.file_helper:
            self.file_helper.send_msg(msg)

    def post_login(self, dump=True):
        self.core.web_init()
        self.core.show_mobile_login()
        self.core.get_contact(True)
        if dump:
            self.core.start_receiving(self.bot_logout)
        self.isLogging = False

        enhance_webwx_request(self)

        self.self = User(self.core.loginInfo['User'], self)
        self.file_helper = Chat(wrap_user_name('filehelper'), self)

        self.start()
        self.register_func()

        add_running_bot(self)

        self.cache_path = 'data/bots/%s.pkl' % self.self.name
        self.enable_puid("data/bots/%s.uid" % self.self.name)

        self.load_config("data/bots/%s.cfg" % self.self.name)

        if dump:
            # self.file_helper.send('🤖️机器人上线了')
            self.dump_login_status(self.cache_path)

    def load_config(self, cfg):
        if os.path.exists(cfg):
            try:
                with open(cfg, 'r') as fp:
                    cfg_dict = json.load(fp)
                    self.master = cfg_dict.get('master')
                    if self.master:
                        set_master_bot(self, dump=False)

                    self.app_id = cfg_dict.get('app_id')
                    self.auto_accept = cfg_dict.get('auto_accept')
                    self.auto_send = cfg_dict.get('auto_send')

            except:
                pass

    def save_config(self):
        cfg = "data/bots/%s.cfg" % self.self.name
        with open(cfg, "w") as fp:
            cfg_dict = {'master': self.master, 'app_id': self.app_id, 'auto_send': self.auto_send,
                        'auto_accept': self.auto_accept, 'crawler_articles': self.crawler_articles}
            json.dump(cfg_dict, fp, ensure_ascii=False, sort_keys=True)

    def register_func(self):
        self.registered.append(MessageConfig(self, bot_func, chats=None, msg_types=None,
                                             except_self=False, run_async=True, enabled=True))

    def bot_logout(self):
        global master_bot

        logger.info("[%s] %s" % (self.bot_name, '退出登录'))

        if master_bot:
            if self == master_bot:
                master_bot.master = False
                master_bot = None
            else:
                master_bot.self.send_msg("🤖️%s 退出了" % self.self.name)

        if self.self.name in running_bots:
            del running_bots[self.self.name]

        # os.remove(self.cache_path)
        if self.core in itchat.instanceList:
            itchat.instanceList.remove(self.core)

        if self in itchat.instanceList:
            itchat.instanceList.remove(self)


master_bot = None
anonymous_bots = defaultdict(AsyncBot)
running_bots = dict()


def set_master_bot(bot, dump=True):
    global master_bot
    bot.master = True
    master_bot = bot
    master_bot.self_msg('🤖️已设置成为监控账号')
    if dump:
        bot.save_config()
