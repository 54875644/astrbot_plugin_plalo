from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 定义一个管理员 QQ 号列表
# 请将这里的 '123456789' 和 '987654321' 替换为你的 Bot 管理员的实际 QQ 号
ADMIN_QQ_NUMBERS = ['你的管理员QQ号1', '你的管理员QQ号2'] 

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_id = event.get_sender_qq_number() # 获取发送者的 QQ 号
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串

        # 检查用户是否是管理员
        if str(user_id) not in ADMIN_QQ_NUMBERS:
            logger.warning(f"用户 {user_name} (QQ: {user_id}) 尝试执行管理员命令 'helloworld' 但没有权限。")
            yield event.plain_result(f"抱歉，{user_name}，你没有权限执行此命令。")
            return # 没有权限则直接返回，不执行后续逻辑

        # 如果是管理员，则继续执行命令逻辑
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
