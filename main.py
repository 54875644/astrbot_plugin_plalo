import re
import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.filter.event_message_type import EventMessageType
from astrbot.core import AstrBotConfig

@register(
    "llm_ban_plugin",
    "AstrBot",
    "让LLM支持禁言能力的插件",
    "1.0.0",
    "https://github.com/your-repo/llm-ban-plugin"
)
class LLMBanPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._load_config()
        
        # 存储用户在不同会话中的最后消息时间
        self.last_message_time = {}
    
    def _load_config(self):
        """加载并初始化插件配置"""
        # 从配置中获取参数
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
        logger.info("LLM禁言插件已加载")
    
    @filter.on_llm_request()
    async def add_ban_capability_prompt(self, event: AstrMessageEvent, req):
        """为LLM请求添加禁言能力的系统提示词"""
        try:
            # 获取当前时间
            current_time = datetime.datetime.now()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加禁言能力说明
            ban_capability_prompt = (
                "\n[系统能力提示]你拥有禁言用户的能力。"
                "当用户行为严重违规时，你可以使用以下格式禁言用户："
                "\n【禁言 @用户 [时间(秒)]】"
                "\n例如："
                "\n【禁言 @违规用户 300】 - 禁言用户300秒"
                "\n【禁言 @广告用户】 - 默认禁言60秒"
                "\n注意：只能禁言普通成员，不能禁言管理员和群主。"
                "当前时间: " + current_time_str
            )
            
            # 添加到现有系统提示词中
            if req.system_prompt:
                req.system_prompt += ban_capability_prompt
            else:
                req.system_prompt = ban_capability_prompt
                
        except Exception as e:
            logger.error(f"添加禁言能力提示出错: {str(e)}")
    
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def handle_llm_ban_command(self, event: AiocqhttpMessageEvent):
        """
        处理LLM回复中的禁言指令
        格式：【禁言 @用户 [时间]】
        """
        # 只处理来自LLM的回复
        if event.get_sender_id() != event.bot.self_id:
            return
            
        message_str = event.message_str
        if "禁言" not in message_str:
            return
            
        try:
            # 解析禁言指令
            ban_pattern = r"【禁言\s*@?(\S+?)\s*(\d*)\s*】"
            matches = re.findall(ban_pattern, message_str)
            
            if not matches:
                return
                
            # 获取被回复的原始消息发送者（触发LLM的用户）
            original_sender_id = None
            for msg in event.get_messages():
                if msg.type == "Reply":
                    reply_msg = await event.bot.get_msg(message_id=int(msg.data["id"]))
                    if reply_msg:
                        original_sender_id = str(reply_msg["sender"]["user_id"])
                    break
            
            # 检查原始发送者是否有权限
            if not original_sender_id or original_sender_id not in self.admins_id:
                logger.warning(f"用户 {original_sender_id} 无权限使用禁言功能")
                return
                
            # 处理所有匹配的禁言指令
            results = []
            for match in matches:
                target_name, ban_time_str = match
                ban_time = int(ban_time_str) if ban_time_str.isdigit() else self.min_ban_time
                ban_time = max(self.min_ban_time, min(ban_time, self.max_ban_time))
                
                # 通过用户名获取用户ID
                target_id = await self.get_user_id_by_name(event, target_name)
                if not target_id:
                    results.append(f"❌ 未找到用户: {target_name}")
                    continue
                    
                # 检查目标用户权限
                target_perm = await self.get_user_permission(event, target_id)
                if target_perm >= self.perm_levels["admin"]:
                    results.append(f"❌ 不能禁言管理员或群主: {target_name}")
                    continue
                
                # 执行禁言操作
                try:
                    await event.bot.set_group_ban(
                        group_id=int(event.get_group_id()),
                        user_id=int(target_id),
                        duration=ban_time
                    )
                    results.append(f"✅ 已禁言用户 {target_name} ({ban_time}秒)")
                except Exception as e:
                    logger.error(f"禁言失败: {e}")
                    results.append(f"❌ 禁言用户 {target_name} 失败: {str(e)}")
            
            # 发送执行结果
            if results:
                yield event.plain_result("\n".join(results))
            
        except Exception as e:
            logger.exception("处理LLM禁言指令时出错")
    
    async def get_user_id_by_name(self, event: AiocqhttpMessageEvent, username: str):
        """通过用户名获取用户ID"""
        try:
            group_id = int(event.get_group_id())
            member_list = await event.bot.get_group_member_list(group_id=group_id)
            
            # 尝试精确匹配
            for member in member_list:
                if member["nickname"] == username or member["card"] == username:
                    return member["user_id"]
            
            # 尝试模糊匹配
            for member in member_list:
                if username in member["nickname"] or username in member["card"]:
                    return member["user_id"]
                    
        except Exception as e:
            logger.error(f"获取用户ID失败: {e}")
            
        return None
    
    async def get_user_permission(self, event: AiocqhttpMessageEvent, user_id: str):
        """获取用户在群内的权限级别"""
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
        self.last_message_time.clear()
