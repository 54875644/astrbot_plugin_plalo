from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.api.star import StarTools
from astrbot.core.star.filter.event_message_type import EventMessageType

@register(
    "LLMBanPlugin",
    "AstrBot",
    "让LLM支持禁言能力的插件",
    "1.0.0",
    "https://github.com/your-repo/llm-ban-plugin"
)
class LLMBanPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 加载配置
        self.config = context.get_config()
        self.admins_id = set(self.config.get("admins_id", []))
        self.min_ban_time = self.config.get("min_ban_time", 60)  # 默认最小禁言时间60秒
        self.max_ban_time = self.config.get("max_ban_time", 600)  # 默认最大禁言时间600秒
        self.allow_self_ban = self.config.get("allow_self_ban", False)  # 是否允许禁言自己
        
        # 权限级别映射
        self.perm_levels = {
            "member": 0,
            "admin": 1,
            "owner": 2
        }
    
    async def initialize(self):
        """插件初始化"""
        logger.info("LLM禁言插件已加载")
    
    @filter.command("禁言")
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def ban_user(self, event: AiocqhttpMessageEvent, ban_time: int = None):
        """
        禁言用户
        用法: /禁言 [@用户] [禁言时间(秒)]
        示例: /禁言 @违规用户 300
        """
        try:
            # 获取发送者权限级别
            sender_perm = await self.get_user_permission(event)
            if sender_perm < self.perm_levels["admin"]:
                yield event.plain_result("❌ 你没有权限使用此命令")
                return
                
            # 解析被禁言用户
            target_ids = self.get_mentioned_users(event)
            
            if not target_ids:
                yield event.plain_result("❌ 请@需要禁言的用户")
                return
                
            # 解析禁言时间
            if ban_time is None:
                ban_time = self.min_ban_time
            else:
                ban_time = max(self.min_ban_time, min(ban_time, self.max_ban_time))
            
            # 执行禁言操作
            group_id = int(event.get_group_id())
            results = []
            
            for user_id in target_ids:
                # 检查是否允许禁言自己
                if not self.allow_self_ban and str(user_id) == event.get_self_id():
                    results.append("❌ 不能禁言机器人自己")
                    continue
                    
                # 检查目标用户权限
                target_perm = await self.get_user_permission(event, user_id)
                if target_perm >= sender_perm:
                    results.append(f"❌ 不能禁言权限相同或更高的用户: {user_id}")
                    continue
                
                try:
                    await event.bot.set_group_ban(
                        group_id=group_id,
                        user_id=int(user_id),
                        duration=ban_time
                    )
                    results.append(f"✅ 已禁言用户 {user_id} ({ban_time}秒)")
                except Exception as e:
                    logger.error(f"禁言失败: {e}")
                    results.append(f"❌ 禁言用户 {user_id} 失败: {str(e)}")
            
            yield event.plain_result("\n".join(results))
            
        except Exception as e:
            logger.exception("禁言命令执行出错")
            yield event.plain_result(f"⚠️ 命令执行出错: {str(e)}")
    
    @filter.command("解禁")
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def unban_user(self, event: AiocqhttpMessageEvent):
        """
        解禁用户
        用法: /解禁 [@用户]
        """
        try:
            # 获取发送者权限级别
            sender_perm = await self.get_user_permission(event)
            if sender_perm < self.perm_levels["admin"]:
                yield event.plain_result("❌ 你没有权限使用此命令")
                return
                
            # 解析被解禁用户
            target_ids = self.get_mentioned_users(event)
            
            if not target_ids:
                yield event.plain_result("❌ 请@需要解禁的用户")
                return
            
            # 执行解禁操作
            group_id = int(event.get_group_id())
            results = []
            
            for user_id in target_ids:
                try:
                    await event.bot.set_group_ban(
                        group_id=group_id,
                        user_id=int(user_id),
                        duration=0  # 0表示解除禁言
                    )
                    results.append(f"✅ 已解禁用户 {user_id}")
                except Exception as e:
                    logger.error(f"解禁失败: {e}")
                    results.append(f"❌ 解禁用户 {user_id} 失败: {str(e)}")
            
            yield event.plain_result("\n".join(results))
            
        except Exception as e:
            logger.exception("解禁命令执行出错")
            yield event.plain_result(f"⚠️ 命令执行出错: {str(e)}")
    
    def get_mentioned_users(self, event: AiocqhttpMessageEvent):
        """从消息中提取被@的用户ID"""
        target_ids = []
        for message in event.get_messages():
            if message.type == "At" and message.data.get("qq") != "all":
                user_id = message.data["qq"]
                if user_id and user_id != event.get_self_id():
                    target_ids.append(user_id)
        return target_ids
    
    async def get_user_permission(self, event: AiocqhttpMessageEvent, user_id: str = None):
        """获取用户在群内的权限级别"""
        if user_id is None:
            user_id = event.get_sender_id()
        
        try:
            member_info = await event.bot.get_group_member_info(
                group_id=int(event.get_group_id()),
                user_id=int(user_id)
            )
            role = member_info.get("role", "member")
            return self.perm_levels.get(role.lower(), 0)
        except Exception:
            return 0  # 默认最低权限
    
    async def terminate(self):
        """插件卸载"""
        logger.info("LLM禁言插件已卸载")
