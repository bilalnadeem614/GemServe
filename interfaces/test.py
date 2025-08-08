from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window

Window.size = (400, 200)

class TestApp(App):
    def build(self):
        return Label(
            text="Hello 👋 World 🌍",
            font_name="assets/NotoColorEmoji.ttf",  # or your font path
            font_size=32
        )

TestApp().run()
