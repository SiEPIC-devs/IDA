# embed8080_in80.py
from remi import start, App
import remi.gui as gui

class Embed8080(App):
    def main(self):
        # 根容器必须是“容器类”，比如 Container / VBox 才能 append
        root = gui.Container(width='100%', height='100%')
        root.style.update({
            'width': '100%', 'height': '100%',
            'margin': '0', 'padding': '0',
            'overflow': 'hidden', 'background': '#f5f5f5'
        })

        # 关键：在你这版 remi 用 Widget(_type='iframe')，不要用 Tag('iframe')
        iframe = gui.Widget(_type='iframe')
        iframe.attributes['src'] = 'http://127.0.0.1:8080'   # 如需局域网访问，换成实际IP
        iframe.attributes['frameborder'] = '0'
        iframe.attributes['width'] = '100%'
        iframe.attributes['height'] = '100%'
        iframe.style['border'] = 'none'
        iframe.style['display'] = 'block'

        root.append(iframe)
        return root

if __name__ == '__main__':
    # 绑定 80 端口通常需要管理员权限
    start(Embed8080, address='0.0.0.0', port=80, start_browser=False, multiple_instance=False)
