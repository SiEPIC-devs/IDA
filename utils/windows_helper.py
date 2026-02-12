import os
import threading
import webview

def launch_window_with_hide(url: str, title: str, width=300, height=260, on_confirm=None):
    """
    Launch a pywebview window that:
      - Hides itself when the user presses X
      - Hides itself when the Remi Confirm button requests a hide
      - Keeps the process alive (runner handles cleanup)

    Usage:
        Simply import this module and call
        
        `launch_window_with_hide(
            url=your_url
            title=your_title
            width=your_width
            height=your_height
            )`
        
        The same way a pywebview window is being
        launched.
    """

    # --- INTERNAL FLAG -----------------------
    # This controls whether the window should hide itself.
    state = {"should_hide": False}

    # --- Called when user clicks X -----------
    def on_close():
        # Just hide the window, DO NOT exit the process
        state["should_hide"] = True
        try:
            wnd.hide()
        except:
            pass

    # --- Called repeatedly by webview loop ---
    def hide_if_requested(window):
        if state["should_hide"]:
            try:
                window.hide()
            except:
                pass

    # --- Small wrapper for Remi confirm -----
    def handle_confirm():
        state["should_hide"] = True
        if on_confirm:
            on_confirm()

    # --- Create window -----------------------
    wnd = webview.create_window(
        title,
        url,
        width=width,
        height=height,
        on_top=True,
        resizable=True,
    )

    # Attach closing event
    wnd.events.closing += on_close

    # Start event loop
    webview.start(
        hide_if_requested,
        wnd
    )

    return handle_confirm
