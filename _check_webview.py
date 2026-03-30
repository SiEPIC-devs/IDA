try:
    import webview
    print("webview version:", webview.__version__)
    import inspect
    sig = inspect.signature(webview.create_window)
    print("create_window params:", list(sig.parameters.keys()))
except Exception as e:
    import traceback
    traceback.print_exc()
