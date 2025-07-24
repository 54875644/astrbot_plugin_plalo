from astrbot.api.event import filter
from astrbot.api.star import register, Context, Star
from astrbot.core.permission import PermissionManager
from aiocqhttp import CQHttp

@register("mcp_group_ban", "YourName", "一个让LLM支持禁言能力的插件，仅适用于aiocqhttp MCP平台", "1.0.0")
class MCPBanPlugin(Star):
    def __init__(self, context: Context, bot: CQHttp):
        super().__init__(context)
        self.bot = bot
        self.context = context

    async def initialize(self):
        """在插件初始化时执行的操作，这里初始化一些可能需要的设置。"""
        pass

    async def execute_ban_user(self, event, duration=None):
        """禁言指定用户命令处理方法"""
        duration = int(duration) if duration else 60
        ats = event.mes.get('at', [])
        msg = f"已将"
        for user in ats:
            user_id = str(user['user_id'])
            try:
                await self.bot.set_group_ban(
                    group_id=event.group_id,
                    user_id=int(user_id),
                    duration=duration
                )
                msg += f" {user_id},"
            except Exception as e:
                logging.error(f"执行禁言时出错：{e}")
        msg += f"设置为禁言状态，时长{duration}秒。"
        await event.send_event(msg)

    @filter.command("禁言")
    async def ban_command(self, event, duration=None):
        """禁言 60 @user"""
        if not duration:
            await event.send_event('你需要提供一个正整数来表示禁言的时长（秒）。默认为60秒。')
            return
        duration = int(duration)
        if await PermissionManager.is_permitted(event.get_sender_id(), 5):  # 假设5为管理员权限
            await self.execute_ban_user(event, duration)
        else:
            await event.send_event("你没有执行该命令的权限。")
