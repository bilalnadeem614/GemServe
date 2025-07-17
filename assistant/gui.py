from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading

from assistant.voice import listen_and_transcribe, speak
from assistant.llm import ask_gemma

class AssistantGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        # Output area
        self.output = Label(size_hint_y=None, text='🔊 Ready.', halign='left', valign='top')
        self.output.bind(texture_size=self._update_label_height)
        scroll = ScrollView(size_hint=(1, 0.6))
        scroll.add_widget(self.output)

        # Text input field
        self.text_input = TextInput(hint_text='Type your message here...', multiline=False, size_hint=(1, 0.1))

        # Buttons
        btn_layout = BoxLayout(size_hint=(1, 0.15), spacing=10)
        self.btn_listen = Button(text='🎤 Speak')
        self.btn_send = Button(text='📤 Send')

        self.btn_listen.bind(on_press=self.start_voice_thread)
        self.btn_send.bind(on_press=self.start_text_thread)

        btn_layout.add_widget(self.btn_listen)
        btn_layout.add_widget(self.btn_send)

        # Add widgets to layout
        self.add_widget(scroll)
        self.add_widget(self.text_input)
        self.add_widget(btn_layout)

    def _update_label_height(self, instance, value):
        self.output.height = self.output.texture_size[1]

    def set_output_text(self, text):
        self.output.text = text
        self.canvas.ask_update()

    def append_output_text(self, text):
        self.output.text += f"\n{text}"
        self.canvas.ask_update()

    # === Voice Thread ===
    def start_voice_thread(self, instance):
        Clock.schedule_once(lambda dt: self.set_output_text("🎙 Listening..."))
        threading.Thread(target=self.process_voice, daemon=True).start()

    def process_voice(self):
        try:
            prompt = listen_and_transcribe()
            Clock.schedule_once(lambda dt: self.set_output_text(f"📝 You said: {prompt}"))
            response = ask_gemma(prompt)
            Clock.schedule_once(lambda dt: self.append_output_text(f"🤖 Gemma3n: {response}"))
            speak(response)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.set_output_text(f"❌ Error: {e}"))

    # === Text Input Thread ===
    def start_text_thread(self, instance):
        prompt = self.text_input.text.strip()
        if prompt:
            self.text_input.text = ""
            Clock.schedule_once(lambda dt: self.set_output_text(f"📝 You typed: {prompt}"))
            threading.Thread(target=self.process_text, args=(prompt,), daemon=True).start()

    def process_text(self, prompt):
        try:
            response = ask_gemma(prompt)
            Clock.schedule_once(lambda dt: self.append_output_text(f"🤖 Gemma3n: {response}"))
            speak(response)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.set_output_text(f"❌ Error: {e}"))

class AssistantApp(App):
    def build(self):
        return AssistantGUI()
