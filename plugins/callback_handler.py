# (c) AlenPaulVarghese
# -*- coding: utf-8 -*-

import asyncio

from pyrogram import filters
from pyrogram.enums import ChatAction
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import Config
from helper import mediagroup_gen
from helper.images import split_image
from helper.keyboard import (
    build_settings_keyboard,
    cycle_render_type,
    cycle_resolution,
    cycle_scroll,
    toggle_options,
    toggle_split,
    cycle_page,
)
from helper.printer import Printer, RenderType, ScrollMode
from plugins.command_handler import feedback
from webshotbot import WebshotBot

_SETTINGS_ATTR = "settings_cache"


def _get_settings(client: WebshotBot, chat_id: int):
    """Read current settings from cache or raise."""
    s = client.settings_cache.get(chat_id)
    if s is None:
        raise RuntimeError("Settings not found — please send the link again.")
    return s


# ── helpers -----------------------------------------------------------


async def _edit_settings(
    client: WebshotBot,
    callback_query: CallbackQuery,
    settings,
):
    """Update cache and re-render keyboard for a settings change."""
    chat_id = callback_query.message.chat.id
    client.settings_cache[chat_id] = settings
    reply_markup = build_settings_keyboard(settings)
    await callback_query.message.edit_text(
        "Choose the prefered settings",
        reply_markup=reply_markup,
    )


async def _upload_result(
    callback_query: CallbackQuery,
    message,
    printer: Printer,
):
    """Upload the rendered file(s) and clean up."""
    await message.edit("**uploading...**")
    if printer.split and printer.fullpage and printer.type.is_image():
        loc_of_images = await asyncio.get_event_loop().run_in_executor(None, split_image, printer.file)
        for media_group in mediagroup_gen(loc_of_images):
            await asyncio.gather(
                callback_query.message.reply_chat_action(ChatAction.UPLOAD_PHOTO),
                callback_query.message.reply_media_group(media_group, disable_notification=True),
            )
    elif printer.type == RenderType.PDF or printer.fullpage:
        await asyncio.gather(
            callback_query.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT),
            callback_query.message.reply_document(str(printer.file)),
        )
    elif not printer.fullpage:
        await asyncio.gather(
            callback_query.message.reply_chat_action(ChatAction.UPLOAD_PHOTO),
            callback_query.message.reply_photo(str(printer.file)),
        )
    await asyncio.gather(
        message.delete(),
        message.reply_text('__Please toggle "Scroll Site" setting if the output has no content.__'),
    )
    printer.cleanup()


# ── primary render handler --------------------------------------------


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "render"))
async def primary_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer("processing your request")
    msg = await callback_query.message.edit("**processing...**")
    settings = _get_settings(client, callback_query.message.chat.id)
    link = callback_query.message.reply_to_message.text
    printer = Printer.from_settings(settings, link)
    printer.allocate_folder(callback_query.message.chat.id, callback_query.message.id)
    await msg.edit("**please wait you are in a queue...**")
    try:
        future, wait_event = client.new_request(printer, callback_query.message.chat.id)
        await wait_event.wait()
        await msg.edit(
            "**rendering the website...**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("render now", "release")]])
            if printer.scroll_control == ScrollMode.MANUAL
            else None,  # type: ignore
        )
        if Config.LOG_GROUP is not None:
            await client.send_message(
                Config.LOG_GROUP,
                printer._get_logstr(
                    callback_query.message.reply_to_message.from_user.id,
                    callback_query.message.reply_to_message.from_user.first_name,
                ),
            )
        await future
    except Exception as e:
        await msg.edit(f"`{e}`")
        printer.cleanup()
        return
    await _upload_result(callback_query, msg, printer)


# ── manual-scroll release ---------------------------------------------


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "release"))
async def release_cb(client: WebshotBot, callback_query: CallbackQuery):
    event = client.get_request(callback_query.message.chat.id)
    if event is not None:
        event.set()
        await callback_query.answer("rendering now")
        await callback_query.message.edit_reply_markup()
    else:
        await callback_query.answer("please wait")


# ── settings toggles --------------------------------------------------


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "format"))
async def format_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, cycle_render_type(settings))


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "page"))
async def page_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, cycle_page(settings))


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "scroll"))
async def scroll_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, cycle_scroll(settings))


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "res"))
async def resolution_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, cycle_resolution(settings))


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "splits"))
async def splits_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, toggle_split(settings))


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "options"))
async def options_cb(client: WebshotBot, callback_query: CallbackQuery):
    await callback_query.answer()
    settings = _get_settings(client, callback_query.message.chat.id)
    await _edit_settings(client, callback_query, toggle_options(settings))


# ── meta actions ------------------------------------------------------


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "cancel"))
async def cancel_cb(_, callback_query: CallbackQuery):
    await callback_query.answer("Canceled your request..!")
    await callback_query.message.delete()


@WebshotBot.on_callback_query(filters.create(lambda _, __, c: c.data == "about_cb"))
async def about_cb(_, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await feedback(_, callback_query.message)


# ── fallback for unknown callback data --------------------------------


@WebshotBot.on_callback_query()
async def unknown_cb(_, callback_query: CallbackQuery):
    await callback_query.answer("unknown action", show_alert=True)
