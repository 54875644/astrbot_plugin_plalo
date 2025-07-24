import logging

from astrbot import register, Context, Star
from aiocqhttp import CQHttp

logger = logging.getLogger(__name__)

@register("mcp_group_ban", "YourName", "一个让LLM支持禁言能力的插件，仅适用于aiocqhttp MCP平台", "1.0.0")
class MCPBanPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.bot: CQHttp = context.get_client()

    async def initialize(self):
        """在插件初始化时执行的操作，这里无需特别操作，可以根据实际情况添加初始化逻辑。"""
        pass

    # 注册指令的装饰器，该指令负责处理禁言操作
    @filter.command("禁言")
    @perm_required(PermLevel.ADMIN)
    async def ban_command(self, event: AiocqhttpMessageEvent, duration: int):
        """执行群聊禁言，被调用时需要一个参数，表示禁言的秒数"""
        # 获取参数中的禁言时长，默认为60秒
        duration = duration or 60
        for tid in get_ats(event):
            # 实际操作禁言
            await self.bot.set_group_ban(
                group_id=int(event.get_group_id()),
                user_id=int(tid),
                duration=duration,
            )
            # 向群聊发送确认消息
            await event.send_event(f"已将【{tid}】设置为禁言状态，时长为{duration}秒")
