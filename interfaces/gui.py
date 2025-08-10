# Librarires for GUI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.clock import Clock
import threading
from kivy.config import Config
from assistant.voice import listen_and_transcribe, speak
from assistant.llm import ask_gemma


# Window.size = (600, 700) # This line of code is for specific window size of the app.
Window.clearcolor = (0.1, 0.1, 0.1, 1)  # Dark background
Window.maximize() # This line of code is for full screen size of the app.
class AssistantGUI(BoxLayout):
    output_text = StringProperty("Welcome to GemServe 👋\n")

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        # Title bar
        title = Label(
            text="🎙️ GemServe - Your Voice Assistant",
            font_name = "seguiemj.ttf",
            size_hint=(1, 0.1),
            font_size='17sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(title)

        # Scrollable output label
        self.output_label = Label(
            text=self.output_text,
            font_name = "seguiemj.ttf",
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=True,
            color=(1, 1, 1, 1)
        )
        self.output_label.bind(texture_size=self._update_label_height)
        scroll = ScrollView(size_hint=(1, 0.65))
        scroll.add_widget(self.output_label)

        self.add_widget(scroll)

        # Voice Button
        self.btn_listen = Button(          
            font_name = "seguiemj.ttf",
            text='🎤 Tap to Speak',
            size_hint=(1, 0.05),
            background_color=(0.2, 0.6, 0.9, 1),
            font_size='18sp',
            bold=True
        )
        self.btn_listen.bind(on_press=self.start_voice_thread)
        self.add_widget(self.btn_listen)

        # Optional: Manual input
        self.input_field = TextInput(
            hint_text="Type a command (optional)...",
            size_hint=(1, 0.07),
            multiline=False,
            background_color=(0.15, 0.15, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            padding=[10, 10]
        )
        self.input_field.bind(on_text_validate=self.on_enter)
        self.add_widget(self.input_field)

    def _update_label_height(self, instance, value):
        self.output_label.height = self.output_label.texture_size[1]
        self.output_label.text_size = (self.output_label.width, None)

    def set_output_text(self, text):
        self.output_label.text = text
        self.canvas.ask_update()

    def append_output_text(self, text):
        self.output_label.text += text + '\n'
        self.canvas.ask_update()

    def start_voice_thread(self, instance):
        Clock.schedule_once(lambda dt: self.append_output_text("[b]🎙 Listening...[/b]"))
        threading.Thread(target=self.process_voice, daemon=True).start()

    def process_voice(self):
        try:
            prompt = listen_and_transcribe()
            Clock.schedule_once(lambda dt: self.append_output_text(f"[color=ffcc00]📝 You: {prompt}[/color]"))
            response = ask_gemma(prompt)
            Clock.schedule_once(lambda dt: self.append_output_text(f"[color=66ff66]🤖 Gemma: {response}[/color]"))
            speak(response)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.append_output_text(f"[color=ff0000]❌ Error: {e}[/color]"))

    def on_enter(self, instance):
        prompt = self.input_field.text.strip()
        if prompt:
            self.input_field.text = ""
            self.append_output_text(f"[color=ffcc00]📝 You: {prompt}[/color]")
            threading.Thread(target=self.process_text_input, args=(prompt,), daemon=True).start()

    def process_text_input(self, prompt):
        try:
            response = ask_gemma(prompt)
            Clock.schedule_once(lambda dt: self.append_output_text(f"[color=66ff66]🤖 Gemma: {response}[/color]"))
            speak(response)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.append_output_text(f"[color=ff0000]❌ Error: {e}[/color]"))


class AssistantApp(App):
    def build(self):
        return AssistantGUI()
