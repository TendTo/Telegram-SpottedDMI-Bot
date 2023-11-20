"""Common info needed in both command and callback handlers"""
from telegram import Bot, CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from spotted.data import Config, PendingPost, PublishedPost, User
from spotted.debug.log_manager import logger
from spotted.utils.keyboard_util import (
    get_approve_kb,
    get_post_outcome_kb,
    get_published_post_kb,
)


class EventInfo:  # pylint: disable=too-many-public-methods
    """Class that contains all the relevant information related to an event"""

    def __init__(
        self,
        bot: Bot,
        ctx: CallbackContext,
        update: Update = None,
        message: Message = None,
        query: CallbackQuery = None,
    ):
        self.__bot = bot
        self.__ctx = ctx
        self.__update = update
        self.__message = message
        self.__query = query

    @property
    def bot(self) -> Bot:
        """Instance of the telegram bot"""
        return self.__bot

    @property
    def context(self) -> CallbackContext:
        """Context generated by some event"""
        return self.__ctx

    @property
    def update(self) -> Update:
        """Update generated by some event"""
        return self.__update

    @property
    def message(self) -> Message:
        """Message that caused the update"""
        return self.__message

    @property
    def bot_data(self) -> dict:
        """Data related to the bot. Is not persistent between restarts"""
        return self.__ctx.bot_data

    @property
    def user_data(self) -> dict:
        """Data related to the user. Is not persistent between restarts"""
        return self.__ctx.user_data

    @property
    def chat_id(self) -> int:
        """Id of the chat where the event happened"""
        if self.__message is None:
            return None
        return self.__message.chat_id

    @property
    def chat_type(self) -> str:
        """Type of the chat where the event happened"""
        if self.__message is None:
            return None
        return self.__message.chat.type

    @property
    def is_private_chat(self) -> bool:
        """Whether the chat is private or not"""

        if self.chat_type is None:
            return None
        return self.chat_type == Chat.PRIVATE

    @property
    def text(self) -> str:
        """Text of the message that caused the update"""
        if self.__message is None:
            return None
        return self.__message.text

    @property
    def callback_key(self) -> str:
        """Return the args of the message that caused the update.
        If the update was caused by a callback, the callback data is splitted by ',' and returned"""
        if self.__query is None or self.__query.data is None:
            return ""
        return self.__query.data.split(",")[0]

    @property
    def args(self) -> list[str]:
        """Return the args of the message that caused the update.
        If the update was caused by a callback, the callback data is splitted by ',' and returned"""
        if self.__query is not None and self.__query.data is not None:
            args = self.__query.data.split(",")
            if len(args) > 1:
                return args[1:]
            return []
        return self.__ctx.args if self.__ctx.args is not None else []

    @property
    def message_id(self) -> int:
        """Id of the message that caused the update"""
        if self.__message is None:
            return None
        return self.__message.message_id

    @property
    def is_valid_message_type(self) -> bool:
        """Whether or not the type of the message is supported"""
        if self.__message is None:
            return False
        return bool(
            self.__message.text
            or self.__message.photo
            or self.__message.voice
            or self.__message.audio
            or self.__message.video
            or self.__message.animation
            or self.__message.sticker
            or self.__message.poll
        )

    @property
    def reply_markup(self) -> InlineKeyboardMarkup:
        """Reply_markup of the message that caused the update"""
        if self.__message is None:
            return None
        return self.__message.reply_markup

    @property
    def user_id(self) -> int:
        """Id of the user that caused the update"""
        if self.__query is not None:
            return self.__query.from_user.id
        if self.__message is not None:
            return self.__message.from_user.id
        return None

    @property
    def user_username(self) -> str:
        """Username of the user that caused the update"""
        if self.__query is not None:
            return self.__query.from_user.username
        if self.__message is not None:
            return self.__message.from_user.username
        return None

    @property
    def user_name(self) -> str:
        """Name of the user that caused the update"""
        if self.__query is not None:
            return self.__query.from_user.name
        if self.__message is not None:
            return self.__message.from_user.name
        return None

    @property
    def inline_keyboard(self) -> InlineKeyboardMarkup:
        """InlineKeyboard attached to the message"""
        if self.__message is None:
            return None
        return self.__message.reply_markup

    @property
    def query_id(self) -> str:
        """Id of the query that caused the update"""
        if self.__query is None:
            return None
        return self.__query.id

    @property
    def query_data(self) -> str:
        """Data associated with the query that caused the update"""
        if self.__query is None:
            return None
        return self.__query.data

    @property
    def forward_from_id(self) -> int:
        """Id of the original message that has been forwarded"""
        if self.__message is None:
            return None
        return self.__message.forward_from_message_id

    @property
    def forward_from_chat_id(self) -> int:
        """Id of the original chat the message has been forwarded from"""
        if self.__message is None or self.__message.forward_from_chat is None:
            return None
        return self.__message.forward_from_chat.id

    @property
    def is_forwarded_post(self) -> bool:
        """Whether the message is in fact a forwarded post from the channel to the group"""
        return self.chat_id == Config.post_get("community_group_id") and self.forward_from_chat_id == Config.post_get(
            "channel_id"
        )

    @classmethod
    def from_message(cls, update: Update, ctx: CallbackContext) -> "EventInfo":
        """Instance of EventInfo created by a message update

        Args:
            update: update event
            context: context passed by the handler

        Returns:
            instance of the class
        """
        message = update.message if update.message is not None else update.edited_message
        return cls(bot=ctx.bot, ctx=ctx, update=update, message=message)

    @classmethod
    def from_callback(cls, update: Update, ctx: CallbackContext) -> "EventInfo":
        """Instance of EventInfo created by a callback update

        Args:
            update: update event
            context: context passed by the handler

        Returns:
            instance of the class
        """
        return cls(
            bot=ctx.bot, ctx=ctx, update=update, message=update.callback_query.message, query=update.callback_query
        )

    @classmethod
    def from_job(cls, ctx: CallbackContext) -> "EventInfo":
        """Instance of EventInfo created by a job update

        Args:
            context: context passed by the handler

        Returns:
            instance of the class
        """
        return cls(bot=ctx.bot, ctx=ctx)

    async def answer_callback_query(self, text: str = None):
        """Calls the answer_callback_query method of the bot class, while also handling the exception

        Args:
            text: Text to show to the user
        """
        try:
            await self.__bot.answer_callback_query(callback_query_id=self.query_id, text=text)
        except BadRequest as ex:
            logger.warning("On answer_callback_query: %s", ex)

    async def edit_inline_keyboard(
        self, chat_id: int = None, message_id: int = None, new_keyboard: InlineKeyboardMarkup = None
    ):
        """Generic wrapper used to edit the inline keyboard of a message with the telegram bot,
        while also handling the exception

        Args:
            chat_id: id of the chat the message to edit belongs to or the current chat if None
            message_id: id of the message to edit. It is the current message if left None
            new_keyboard: new inline keyboard to assign to the message
        """
        chat_id = chat_id if chat_id is not None else self.chat_id
        message_id = message_id if message_id is not None else self.message_id
        try:
            await self.__bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=new_keyboard
            )
        except BadRequest as ex:
            logger.error("EventInfo.edit_inline_keyboard: %s", ex)

    async def send_post_to_admins(self) -> bool:
        """Sends the post to the admin group, so it can be approved

        Returns:
            whether or not the operation was successful
        """
        message = self.__message.reply_to_message
        admin_group_id = Config.post_get("admin_group_id")
        poll = message.poll  # if the message is a poll, get its reference

        try:
            if poll:  # makes sure the poll is anonym
                g_message = await self.__bot.send_poll(
                    chat_id=admin_group_id,
                    question=poll.question,
                    options=[option.text for option in poll.options],
                    type=poll.type,
                    allows_multiple_answers=poll.allows_multiple_answers,
                    correct_option_id=poll.correct_option_id,
                    reply_markup=get_approve_kb(),
                )
            elif message.text and message.entities:  # maintains the previews, if present
                show_preview = self.user_data.get("show_preview", True)
                g_message = await self.__bot.send_message(
                    chat_id=admin_group_id,
                    text=message.text,
                    reply_markup=get_approve_kb(),
                    entities=message.entities,
                    disable_web_page_preview=not show_preview,
                )
            else:
                g_message = await self.__bot.copy_message(
                    chat_id=admin_group_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                    reply_markup=get_approve_kb(),
                )
        except BadRequest as ex:
            logger.error("Sending the post on send_post_to: %s", ex)
            return False

        PendingPost.create(user_message=message, admin_group_id=admin_group_id, g_message_id=g_message.message_id)

        return True

    async def send_post_to_channel(self, user_id: int):
        """Sends the post to  the channel, so it can be enjoyed by the users (and voted, if comments are disabled)"""

        message = self.__message
        channel_id = Config.post_get("channel_id")
        poll = message.poll  # if the message is a poll, get its reference

        reply_markup = None
        # ... append the voting Inline Keyboard, if comments are not to be supported
        if not Config.post_get("comments"):
            reply_markup = get_published_post_kb()
        if poll:  # makes sure the poll is anonym
            c_message = await self.__bot.send_poll(
                chat_id=channel_id,
                question=poll.question,
                options=[option.text for option in poll.options],
                type=poll.type,
                allows_multiple_answers=poll.allows_multiple_answers,
                correct_option_id=poll.correct_option_id,
                reply_markup=reply_markup,
            )
        else:
            c_message = await self.__bot.copy_message(
                chat_id=channel_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
                reply_markup=reply_markup,
            )

        if not Config.post_get("comments"):  # if the user can vote directly on the post
            PublishedPost.create(c_message_id=c_message.message_id, channel_id=channel_id)
        else:  # ... else, if comments are enabled, save the user_id, so the user can be credited
            self.bot_data[f"{channel_id},{c_message.message_id}"] = user_id

    async def send_post_to_channel_group(self):
        """Sends the post to the group associated to the channel,
        so that users can vote the post (if comments are enabled)
        """

        message = self.__message
        community_group_id = Config.post_get("community_group_id")
        user_id = self.bot_data.pop(f"{self.forward_from_chat_id},{self.forward_from_id}", -1)

        sign = await User(user_id).get_user_sign(bot=self.__bot)
        post_message = await self.__bot.send_message(
            chat_id=community_group_id,
            text=f"by: {sign}",
            reply_markup=get_published_post_kb(),
            reply_to_message_id=message.message_id,
        )

        PublishedPost.create(channel_id=community_group_id, c_message_id=post_message.message_id)

    async def show_admins_votes(self, pending_post: PendingPost, reason: str | None = None):
        """After a post is been approved or rejected, shows the admins that approved or rejected it \
            and edit the message to show the admin's votes

        Args:
            pending_post: post to show the admin's votes for
            reason: reason for the rejection, currently used on autoreply
        """
        inline_keyboard = await get_post_outcome_kb(
            bot=self.__bot, votes=pending_post.get_list_admin_votes(), reason=reason
        )

        await self.__bot.edit_message_reply_markup(
            chat_id=pending_post.admin_group_id, message_id=pending_post.g_message_id, reply_markup=inline_keyboard
        )

        remaining_pending_posts = PendingPost.get_all(admin_group_id=pending_post.admin_group_id)

        # remove the post from the pending posts
        remaining_pending_posts = [
            post for post in remaining_pending_posts if post.g_message_id != pending_post.g_message_id
        ]

        remaining_pending_posts.sort(key=lambda post: post.g_message_id)

        remaining_pending_posts_count = len(remaining_pending_posts)

        # if there are pending post, reply to the oldest one with the number of remaining pending posts
        if remaining_pending_posts_count > 0:
            text = f"⬆️ Post in attesa\nRimangono {remaining_pending_posts_count} post in attesa"
            oldest_pending_post = remaining_pending_posts[0]

            await self.__bot.send_message(
                chat_id=pending_post.admin_group_id, text=text, reply_to_message_id=oldest_pending_post.g_message_id
            )
