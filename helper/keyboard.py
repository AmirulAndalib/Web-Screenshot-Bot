# (c) AlenPaulVarghese
# -*- coding: utf-8 -*-

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from helper.printer import CacheData, RenderType, ScrollMode


def build_settings_keyboard(settings: CacheData) -> InlineKeyboardMarkup:
    """Build the settings keyboard from cached user settings.

    Produces a consistent keyboard layout so that no handler
    needs to mutate by hardcoded index.
    """
    render_type = settings["render_type"]
    fullpage = settings["fullpage"]
    scroll_control = settings["scroll_control"]
    resolution = settings["resolution"]
    split = settings["split"]

    # Row 0 – format
    row0 = [InlineKeyboardButton(f"Format - {render_type.name.upper()}", "format")]

    # Row 1 – page (full / partial)
    row1 = [
        InlineKeyboardButton(
            f"Page - {'Full' if fullpage else 'Partial'}",
            "page",
        )
    ]

    # Row 2 – scroll mode
    row2 = [InlineKeyboardButton(f"Scroll Site - {scroll_control.value.title()}", "scroll")]

    # Row 3 – options toggle
    show_options = settings.get("show_options", False)
    options_text = "hide additional options ˄" if show_options else "show additional options ˅"
    row3 = [InlineKeyboardButton(options_text, "options")]

    markup = [row0, row1, row2, row3]

    # Rows 4+ – additional options (visible when toggled on)
    if show_options:
        markup.append([InlineKeyboardButton(f"resolution | {resolution}", "res")])
        if render_type != RenderType.PDF:
            markup.append([InlineKeyboardButton(f"Split - {'Yes' if split else 'No'}", "splits")])

    # Penultimate row – start render
    markup.append([InlineKeyboardButton("▫️ start render ▫️", "render")])
    # Last row – cancel
    markup.append([InlineKeyboardButton("cancel", "cancel")])

    return InlineKeyboardMarkup(markup)


# ── helpers for individual toggles ---------------------------------

def cycle_render_type(settings: CacheData) -> CacheData:
    mapping = {RenderType.PDF: RenderType.PNG, RenderType.PNG: RenderType.JPEG, RenderType.JPEG: RenderType.PDF}
    new_type = mapping[settings["render_type"]]

    if new_type == RenderType.PDF:
        new_res = "Letter"
    else:
        new_res = "1280x720"
    new_split = settings["split"] if new_type != RenderType.PDF else False

    return CacheData(
        render_type=new_type,
        fullpage=settings["fullpage"],
        scroll_control=settings["scroll_control"],
        resolution=new_res,
        split=new_split,
        show_options=settings.get("show_options", False),
    )


def cycle_page(settings: CacheData) -> CacheData:
    return CacheData(
        render_type=settings["render_type"],
        fullpage=not settings["fullpage"],
        scroll_control=settings["scroll_control"],
        resolution=settings["resolution"],
        split=settings["split"],
        show_options=settings.get("show_options", False),
    )


def cycle_scroll(settings: CacheData) -> CacheData:
    mapping = {ScrollMode.OFF: ScrollMode.AUTO, ScrollMode.AUTO: ScrollMode.MANUAL, ScrollMode.MANUAL: ScrollMode.OFF}
    return CacheData(
        render_type=settings["render_type"],
        fullpage=settings["fullpage"],
        scroll_control=mapping[settings["scroll_control"]],
        resolution=settings["resolution"],
        split=settings["split"],
        show_options=settings.get("show_options", False),
    )


def toggle_split(settings: CacheData) -> CacheData:
    return CacheData(
        render_type=settings["render_type"],
        fullpage=settings["fullpage"],
        scroll_control=settings["scroll_control"],
        resolution=settings["resolution"],
        split=not settings["split"],
        show_options=settings.get("show_options", False),
    )


_RES_IMAGE = ["800x600", "1280x720", "1920x1080", "2560x1440"]
_RES_PDF = ["Letter", "Legal", "A4", "A5"]


def cycle_resolution(settings: CacheData) -> CacheData:
    pool = _RES_PDF if settings["render_type"] == RenderType.PDF else _RES_IMAGE
    idx = pool.index(settings["resolution"])
    next_res = pool[(idx + 1) % len(pool)]
    return CacheData(
        render_type=settings["render_type"],
        fullpage=settings["fullpage"],
        scroll_control=settings["scroll_control"],
        resolution=next_res,
        split=settings["split"],
        show_options=settings.get("show_options", False),
    )


def toggle_options(settings: CacheData) -> CacheData:
    currently_showing = settings.get("show_options", False)
    if currently_showing:
        return CacheData(
            render_type=settings["render_type"],
            fullpage=settings["fullpage"],
            scroll_control=settings["scroll_control"],
            resolution="Letter",
            split=False,
            show_options=False,
        )
    default_res = "Letter" if settings["render_type"] == RenderType.PDF else "1280x720"
    return CacheData(
        render_type=settings["render_type"],
        fullpage=settings["fullpage"],
        scroll_control=settings["scroll_control"],
        resolution=default_res,
        split=False,
        show_options=True,
    )
