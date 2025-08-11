# # ======================
# # GemServe Voice Assistant GUI
# # ======================

# from kivy.app import App
# from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.label import Label
# from kivy.uix.button import Button
# from kivy.uix.scrollview import ScrollView
# from kivy.uix.textinput import TextInput
# from kivy.core.window import Window
# from kivy.properties import StringProperty
# from kivy.clock import Clock
# from kivy.metrics import dp
# import threading

# # Import your assistant logic
# from assistant.voice import listen_and_transcribe, speak
# from assistant.llm import ask_gemma

# # Window setup
# Window.clearcolor = (0.1, 0.1, 0.1, 1)  # Dark background
# Window.maximize()

# class AssistantGUI(BoxLayout):
#     output_text = StringProperty("Welcome to GemServe 👋\n")

#     def __init__(self, **kwargs):
#         super().__init__(orientation='vertical', padding=dp(10), spacing=dp(10), **kwargs)

#         # ===== Title bar =====
#         title = Label(
#             text="🎙️ GemServe - Your Voice Assistant",
#             font_name="seguiemj.ttf",
#             size_hint=(1, 0.1),
#             font_size=dp(20),
#             bold=True,
#             color=(1, 1, 1, 1)
#         )
#         self.add_widget(title)

#         # ===== Scrollable Output =====
#         self.output_label = Label(
#             text=self.output_text,
#             font_name="seguiemj.ttf",
#             size_hint_y=None,
#             halign='left',
#             valign='top',
#             markup=True,
#             font_size=dp(16),
#             color=(1, 1, 1, 1)
#         )
#         self.output_label.bind(texture_size=self._update_label_height)

#         self.scroll = ScrollView(size_hint=(1, 0.65))
#         self.scroll.add_widget(self.output_label)
#         self.add_widget(self.scroll)

#         # ===== Voice Button =====
#         self.btn_listen = Button(
#             font_name="seguiemj.ttf",
#             text='🎤 Tap to Speak',
#             size_hint=(1, 0.07),
#             background_color=(0.2, 0.6, 0.9, 1),
#             font_size=dp(18),
#             bold=True
#         )
#         self.btn_listen.bind(on_press=self.start_voice_thread)
#         self.add_widget(self.btn_listen)

#         # ===== Manual Input Field =====
#         self.input_field = TextInput(
#             hint_text="Type a command (optional)...",
#             size_hint=(1, 0.07),
#             multiline=False,
#             background_color=(0.15, 0.15, 0.15, 1),
#             foreground_color=(1, 1, 1, 1),
#             font_size=dp(16),
#             padding=[dp(10), dp(10)]
#         )
#         self.input_field.bind(on_text_validate=self.on_enter)
#         self.add_widget(self.input_field)

#     # ===== Utility: Update Label Height =====
#     def _update_label_height(self, instance, value):
#         self.output_label.height = self.output_label.texture_size[1]
#         self.output_label.text_size = (self.output_label.width, None)
#         # Auto-scroll to bottom
#         Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0))

#     # ===== Utility: Set or Append Output =====
#     def set_output_text(self, text):
#         self.output_label.text = text
#         self.canvas.ask_update()

#     def append_output_text(self, text):
#         self.output_label.text += text + '\n'
#         self.canvas.ask_update()

#     # ===== Voice Handling =====
#     def start_voice_thread(self, instance):
#         Clock.schedule_once(lambda dt: self.append_output_text("[b]🎙 Listening...[/b]"))
#         threading.Thread(target=self.process_voice, daemon=True).start()

#     def process_voice(self):
#         try:
#             prompt = listen_and_transcribe()
#             Clock.schedule_once(lambda dt: self.append_output_text(
#                 f"[color=ffcc00]📝 You: {prompt}[/color]"
#             ))
#             response = ask_gemma(prompt)
#             Clock.schedule_once(lambda dt: self.append_output_text(
#                 f"[color=66ff66]🤖 Gemma: {response}[/color]"
#             ))
#             speak(response)
#         except Exception as e:
#             Clock.schedule_once(lambda dt: self.append_output_text(
#                 f"[color=ff0000]❌ Error: {e}[/color]"
#             ))

#     # ===== Manual Text Input Handling =====
#     def on_enter(self, instance):
#         prompt = self.input_field.text.strip()
#         if prompt:
#             self.input_field.text = ""
#             self.append_output_text(f"[color=ffcc00]📝 You: {prompt}[/color]")
#             threading.Thread(target=self.process_text_input, args=(prompt,), daemon=True).start()

#     def process_text_input(self, prompt):
#         try:
#             response = ask_gemma(prompt)
#             Clock.schedule_once(lambda dt: self.append_output_text(
#                 f"[color=66ff66]🤖 Gemma: {response}[/color]"
#             ))
#             speak(response)
#         except Exception as e:
#             Clock.schedule_once(lambda dt: self.append_output_text(
#                 f"[color=ff0000]❌ Error: {e}[/color]"
#             ))


# class AssistantApp(App):
#     def build(self):
#         return AssistantGUI()

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window

# Default Dark Theme
Window.clearcolor = (0.1, 0.1, 0.1, 1)
Window.maximize()


# ===== MAIN SCREEN =====
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Greeting
        greeting = Label(
            text="Hi, welcome to GemServe 👋",
            font_size='20sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.1)
        )
        layout.add_widget(greeting)

        # Panels
        panels = BoxLayout(size_hint=(1, 0.85), spacing=10)

        # Chat Panel
        chat_box = BoxLayout(orientation='vertical', padding=5, spacing=5)
        chat_label = Label(text="💬 Chat", size_hint=(1, 0.1), bold=True, color=(1, 1, 1, 1))
        chat_box.add_widget(chat_label)

        chat_scroll = ScrollView(size_hint=(1, 0.8))
        chat_content = GridLayout(cols=1, spacing=5, size_hint_y=None)
        chat_content.bind(minimum_height=chat_content.setter('height'))
        for i in range(5):
            chat_content.add_widget(Label(text=f"Chat {i+1}", size_hint_y=None, height=40, color=(1, 1, 1, 1)))
        chat_scroll.add_widget(chat_content)
        chat_box.add_widget(chat_scroll)

        chat_add_btn = Button(
            text="+", size_hint=(1, 0.1),
            background_color=(0.2, 0.6, 0.9, 1),
            font_size='20sp',
            on_press=lambda x: self.goto_chat()
        )
        chat_box.add_widget(chat_add_btn)
        panels.add_widget(chat_box)

        # To-do Panel
        todo_box = BoxLayout(orientation='vertical', padding=5, spacing=5)
        todo_label = Label(text="📝 To-do", size_hint=(1, 0.1), bold=True, color=(1, 1, 1, 1))
        todo_box.add_widget(todo_label)

        todo_scroll = ScrollView(size_hint=(1, 0.8))
        todo_content = GridLayout(cols=1, spacing=5, size_hint_y=None)
        todo_content.bind(minimum_height=todo_content.setter('height'))
        for i in range(5):
            todo_content.add_widget(Label(text=f"Task {i+1}", size_hint_y=None, height=40, color=(1, 1, 1, 1)))
        todo_scroll.add_widget(todo_content)
        todo_box.add_widget(todo_scroll)

        todo_add_btn = Button(
            text="+", size_hint=(1, 0.1),
            background_color=(0.2, 0.8, 0.4, 1),
            font_size='20sp',
            on_press=lambda x: self.goto_todo()
        )
        todo_box.add_widget(todo_add_btn)
        panels.add_widget(todo_box)

        layout.add_widget(panels)
        self.add_widget(layout)

    def goto_chat(self):
        self.manager.current = "chat"

    def goto_todo(self):
        self.manager.current = "todo"


# ===== CHAT SCREEN =====
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        layout.add_widget(Label(
            text="💬 Chat Screen",
            font_size='20sp',
            color=(1, 1, 1, 1),
            size_hint=(1, 0.1)
        ))

        back_btn = Button(
    text="⬅ Back",
    size_hint=(1, 0.01),
    on_press=lambda x: setattr(self.manager, "current", "main")
)

        layout.add_widget(back_btn)

        self.add_widget(layout)


# ===== TO-DO SCREEN =====
class TodoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        layout.add_widget(Label(
            text="📝 To-do Screen",
            font_size='20sp',
            color=(1, 1, 1, 1),
            size_hint=(1, 0.1)
        ))

        back_btn = Button(
            text="⬅ Back",
            size_hint=(1, 0.01),
            on_press=lambda x: setattr(self.manager, "current", "main")
        )

        layout.add_widget(back_btn)

        self.add_widget(layout)


# ===== APP =====
class GemServeApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(ChatScreen(name="chat"))
        sm.add_widget(TodoScreen(name="todo"))
        return sm

